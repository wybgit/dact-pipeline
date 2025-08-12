import subprocess
import os
import glob
import re
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment
from dact.models import Tool
from dact.logger import log

def find_file(dir: str, pattern: str) -> str:
    """
    Finds a single file matching a glob pattern in a directory.
    Raises FileNotFoundError if no file is found.
    Returns the first file if multiple are found.
    """
    # Ensure dir is an absolute path before using glob
    search_path = os.path.join(dir, pattern)
    files = glob.glob(search_path)
    if not files:
        raise FileNotFoundError(f"No file found for pattern '{pattern}' in directory '{dir}'")
    # In the future, we might want to warn the user about multiple files.
    return files[0]

def find_latest_file(dir: str, pattern: str) -> str:
    """
    Finds the most recently created file matching a glob pattern in a directory.
    Supports recursive search with ** pattern.
    Raises FileNotFoundError if no file is found.
    """
    if "**" in pattern:
        search_path = os.path.join(dir, pattern)
        files = glob.glob(search_path, recursive=True)
    else:
        search_path = os.path.join(dir, pattern)
        files = glob.glob(search_path)
    
    if not files:
        raise FileNotFoundError(f"No file found for pattern '{pattern}' in directory '{dir}'")
    
    # Return the most recently created file
    return max(files, key=os.path.getctime)

def find_onnx_file(dir: str, pattern: str = "**/*.onnx") -> str:
    """
    Dynamically finds ONNX files with support for dynamic folder names.
    Supports patterns like Conv_testcase_98bd3f/resources/Conv_testcase_98bd3f.onnx
    Returns the most recently created ONNX file.
    """
    search_path = os.path.join(dir, pattern)
    files = glob.glob(search_path, recursive=True)
    
    if not files:
        raise FileNotFoundError(f"No ONNX file found for pattern '{pattern}' in directory '{dir}'")
    
    # Return the most recently created ONNX file
    return max(files, key=os.path.getctime)

def find_onnx_dir(dir: str, pattern: str = "**/*.onnx") -> str:
    """
    Finds the directory containing an ONNX file.
    Returns the directory path of the most recently created ONNX file.
    """
    onnx_file = find_onnx_file(dir, pattern)
    return os.path.dirname(onnx_file)

def check_file_exists(path: str) -> bool:
    """
    Checks if a file or directory exists.
    Returns True if the path exists, False otherwise.
    """
    return os.path.exists(path)

# A registry of safe functions that can be called in post_exec
POST_EXEC_FUNCTIONS = {
    "find_file": find_file,
    "find_latest_file": find_latest_file,
    "find_onnx_file": find_onnx_file,
    "find_onnx_dir": find_onnx_dir,
    "check_file_exists": check_file_exists,
}

class Executor:
    """
    Executes a single tool step.
    """
    def __init__(self, tool: Tool, params: Dict[str, Any]):
        self.tool = tool
        self.params = params
        # Using an empty loader as templates are passed as strings
        self.jinja_env = Environment()

    def _resolve_post_exec(self, work_dir: Path) -> Dict[str, Any]:
        """Resolves the post_exec outputs."""
        if not self.tool.post_exec:
            return {}

        outputs = {}
        for name, rule in self.tool.post_exec.outputs.items():
            # For now, we only support a simple function call format like `find_file(...)`
            match = re.match(r"(\w+)\((.*)\)", rule)
            if not match:
                continue

            func_name, args_str = match.groups()
            if func_name not in POST_EXEC_FUNCTIONS:
                continue

            try:
                # Parse arguments like `dir='outputs', pattern='{{ filename }}'`
                args_re = re.compile(r"(\w+)\s*=\s*'([^']*)'")
                args = dict(args_re.findall(args_str))

                # Render any jinja variables within the arguments themselves
                rendered_args = {}
                for k, v in args.items():
                    template = self.jinja_env.from_string(v)
                    # The params for rendering are the *initial* params for the tool
                    rendered_args[k] = template.render(**self.params)

                # Make 'dir' path absolute by resolving it against the step's working directory
                if 'dir' in rendered_args:
                    # Path() handles absolute vs relative paths correctly.
                    rendered_args['dir'] = str(work_dir / rendered_args['dir'])

                func = POST_EXEC_FUNCTIONS[func_name]
                outputs[name] = func(**rendered_args)
            except Exception as e:
                raise RuntimeError(f"Failed to resolve post_exec output '{name}' with rule '{rule}': {e}") from e
        return outputs

    def _validate_result(self, result: Dict[str, Any], work_dir: Path) -> Dict[str, Any]:
        """
        Validates the execution result against tool validation rules.
        Returns validation results with success status and details.
        """
        if not self.tool.validation:
            return {"success": True, "details": "No validation rules defined"}
        
        validation = self.tool.validation
        validation_results = []
        overall_success = True
        
        # Check exit code
        if validation.exit_code is not None:
            expected_code = validation.exit_code
            actual_code = result["returncode"]
            success = actual_code == expected_code
            validation_results.append({
                "rule": "exit_code",
                "expected": expected_code,
                "actual": actual_code,
                "success": success
            })
            if not success:
                overall_success = False
        
        # Check stdout contains patterns
        if validation.stdout_contains:
            stdout = result["stdout"]
            for pattern in validation.stdout_contains:
                success = pattern in stdout
                validation_results.append({
                    "rule": "stdout_contains",
                    "pattern": pattern,
                    "success": success
                })
                if not success:
                    overall_success = False
        
        # Check stderr does not contain patterns
        if validation.stderr_not_contains:
            stderr = result["stderr"]
            for pattern in validation.stderr_not_contains:
                success = pattern not in stderr
                validation_results.append({
                    "rule": "stderr_not_contains",
                    "pattern": pattern,
                    "success": success
                })
                if not success:
                    overall_success = False
        
        # Check output files exist
        if validation.output_files_exist:
            for file_pattern in validation.output_files_exist:
                try:
                    # Render the file pattern with current params
                    template = self.jinja_env.from_string(file_pattern)
                    rendered_pattern = template.render(**self.params)
                    
                    # Check if file exists (support glob patterns)
                    if "*" in rendered_pattern or "?" in rendered_pattern:
                        search_path = str(work_dir / rendered_pattern)
                        # Use recursive=True for patterns containing **
                        if "**" in rendered_pattern:
                            files = glob.glob(search_path, recursive=True)
                        else:
                            files = glob.glob(search_path)
                        success = len(files) > 0
                        validation_results.append({
                            "rule": "output_files_exist",
                            "pattern": rendered_pattern,
                            "found_files": files,
                            "success": success
                        })
                    else:
                        file_path = work_dir / rendered_pattern
                        success = file_path.exists()
                        validation_results.append({
                            "rule": "output_files_exist",
                            "file": rendered_pattern,
                            "success": success
                        })
                    
                    if not success:
                        overall_success = False
                        
                except Exception as e:
                    validation_results.append({
                        "rule": "output_files_exist",
                        "pattern": file_pattern,
                        "error": str(e),
                        "success": False
                    })
                    overall_success = False
        
        # Check success/failure patterns if defined
        if self.tool.success_pattern and result["returncode"] == 0:
            success = bool(re.search(self.tool.success_pattern, result["stdout"]))
            validation_results.append({
                "rule": "success_pattern",
                "pattern": self.tool.success_pattern,
                "success": success
            })
            if not success:
                overall_success = False
        
        if self.tool.failure_pattern and result["returncode"] != 0:
            success = not bool(re.search(self.tool.failure_pattern, result["stderr"]))
            validation_results.append({
                "rule": "failure_pattern",
                "pattern": self.tool.failure_pattern,
                "success": success
            })
            if not success:
                overall_success = False
        
        return {
            "success": overall_success,
            "details": validation_results
        }

    def execute(self, work_dir: Path) -> Dict[str, Any]:
        """
        Renders the command and executes it in a specific working directory.
        """
        template = self.jinja_env.from_string(self.tool.command_template)
        rendered_command = template.render(**self.params)

        # Log the command execution
        log.info(f"Executing command: [cyan]{rendered_command}[/cyan] in [cyan]{work_dir}[/cyan]")

        # Handle timeout if specified
        timeout = self.tool.timeout
        
        result = subprocess.run(
            rendered_command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=work_dir,  # Execute the command in the specified working directory
            timeout=timeout
        )

        # Save stdout and stderr to log files
        with open(work_dir / "stdout.log", "w") as f:
            f.write(result.stdout)
        with open(work_dir / "stderr.log", "w") as f:
            f.write(result.stderr)

        outputs = self._resolve_post_exec(work_dir)
        
        # Perform validation
        validation_result = self._validate_result({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "command": rendered_command,
            "outputs": outputs,
        }, work_dir)

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "command": rendered_command,
            "outputs": outputs,
            "validation": validation_result,
        }