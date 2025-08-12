import pytest
from pathlib import Path
from dact.models import Tool, ToolValidation
from dact.executor import Executor, find_onnx_file, find_onnx_dir, find_latest_file, check_file_exists
from dact.tool_loader import load_tools_from_directory

def test_enhanced_tool_loading():
    """Test that enhanced tools can be loaded from directory."""
    tools = load_tools_from_directory('tools')
    
    # Check that our enhanced tools are loaded
    assert 'ai-json-operator' in tools
    assert 'atc' in tools
    assert 'file-validator' in tools
    
    # Check that validation rules are properly loaded
    ai_tool = tools['ai-json-operator']
    assert ai_tool.validation is not None
    assert ai_tool.validation.exit_code == 0
    assert 'generated' in ai_tool.validation.stdout_contains
    
    atc_tool = tools['atc']
    assert atc_tool.validation is not None
    assert atc_tool.timeout == 300
    assert 'FATAL' in atc_tool.validation.stderr_not_contains

def test_e2e_onnx_simulation(tmp_path: Path):
    """Test end-to-end ONNX file generation and discovery simulation."""
    # Simulate the ai-json-operator tool creating ONNX files
    # Create the expected directory structure that ai-json-operator would create
    output_dir = tmp_path / "outputs"
    model_dir = output_dir / "Conv_testcase_98bd3f" / "resources"
    model_dir.mkdir(parents=True)
    
    # Create a fake ONNX file
    onnx_file = model_dir / "Conv_testcase_98bd3f.onnx"
    onnx_file.write_text("fake onnx model content")
    
    # Test tool that simulates ai-json-operator behavior
    tool_data = {
        "name": "mock-ai-json-operator",
        "command_template": "echo 'Model successfully generated'",
        "validation": {
            "exit_code": 0,
            "stdout_contains": ["successfully generated"],
            "output_files_exist": ["{{ output_dir }}/**/*.onnx"]
        },
        "post_exec": {
            "outputs": {
                "onnx_file": "find_onnx_file(dir='{{ output_dir }}')",
                "onnx_dir": "find_onnx_dir(dir='{{ output_dir }}')"
            }
        }
    }
    
    tool = Tool(**tool_data)
    executor = Executor(tool=tool, params={"output_dir": "outputs"})
    
    result = executor.execute(work_dir=tmp_path)
    
    # Verify execution was successful
    assert result["returncode"] == 0
    assert result["validation"]["success"] is True
    
    # Verify post_exec outputs were correctly resolved
    assert "onnx_file" in result["outputs"]
    assert "onnx_dir" in result["outputs"]
    assert result["outputs"]["onnx_file"] == str(onnx_file)
    assert result["outputs"]["onnx_dir"] == str(model_dir)
    
    # Verify validation rules passed
    validation_details = result["validation"]["details"]
    exit_code_check = next(r for r in validation_details if r["rule"] == "exit_code")
    assert exit_code_check["success"] is True
    
    stdout_check = next(r for r in validation_details if r["rule"] == "stdout_contains")
    assert stdout_check["success"] is True
    
    file_check = next(r for r in validation_details if r["rule"] == "output_files_exist")
    assert file_check["success"] is True

def test_atc_tool_simulation(tmp_path: Path):
    """Test ATC tool simulation with validation."""
    # Create input ONNX file
    onnx_file = tmp_path / "input.onnx"
    onnx_file.write_text("fake onnx content")
    
    # Create expected output directory
    output_dir = tmp_path / "atc_outputs"
    output_dir.mkdir()
    
    # Create expected .om file
    om_file = output_dir / "model.om"
    om_file.write_text("fake om content")
    
    # Test tool that simulates ATC behavior
    tool_data = {
        "name": "mock-atc",
        "command_template": "echo 'ATC run success: model compiled'",
        "validation": {
            "exit_code": 0,
            "stdout_contains": ["ATC run success"],
            "stderr_not_contains": ["FATAL", "ERROR"],
            "output_files_exist": ["{{ output }}/*.om"]
        }
    }
    
    tool = Tool(**tool_data)
    executor = Executor(tool=tool, params={
        "model": str(onnx_file),
        "output": "atc_outputs"
    })
    
    result = executor.execute(work_dir=tmp_path)
    
    # Verify execution was successful
    assert result["returncode"] == 0
    assert result["validation"]["success"] is True
    
    # Verify all validation rules passed
    validation_details = result["validation"]["details"]
    
    # Check exit code validation
    exit_code_check = next(r for r in validation_details if r["rule"] == "exit_code")
    assert exit_code_check["success"] is True
    
    # Check stdout contains validation
    stdout_checks = [r for r in validation_details if r["rule"] == "stdout_contains"]
    assert all(check["success"] for check in stdout_checks)
    
    # Check stderr not contains validation
    stderr_checks = [r for r in validation_details if r["rule"] == "stderr_not_contains"]
    assert all(check["success"] for check in stderr_checks)
    
    # Check output files exist validation
    file_checks = [r for r in validation_details if r["rule"] == "output_files_exist"]
    assert all(check["success"] for check in file_checks)

def test_complex_validation_failure_scenarios(tmp_path: Path):
    """Test various validation failure scenarios."""
    
    # Test 1: Exit code mismatch
    tool_data = {
        "name": "fail-tool",
        "command_template": "exit 1",
        "validation": {
            "exit_code": 0
        }
    }
    tool = Tool(**tool_data)
    executor = Executor(tool=tool, params={})
    result = executor.execute(work_dir=tmp_path)
    
    assert result["validation"]["success"] is False
    exit_code_check = next(r for r in result["validation"]["details"] if r["rule"] == "exit_code")
    assert exit_code_check["success"] is False
    assert exit_code_check["expected"] == 0
    assert exit_code_check["actual"] == 1
    
    # Test 2: Missing output files
    tool_data = {
        "name": "no-output-tool",
        "command_template": "echo 'no files created'",
        "validation": {
            "output_files_exist": ["missing_file.txt"]
        }
    }
    tool = Tool(**tool_data)
    executor = Executor(tool=tool, params={})
    result = executor.execute(work_dir=tmp_path)
    
    assert result["validation"]["success"] is False
    file_check = next(r for r in result["validation"]["details"] if r["rule"] == "output_files_exist")
    assert file_check["success"] is False
    
    # Test 3: Stderr contains forbidden patterns
    tool_data = {
        "name": "error-tool",
        "command_template": "echo 'FATAL ERROR: something went wrong' >&2",
        "validation": {
            "stderr_not_contains": ["FATAL", "ERROR"]
        }
    }
    tool = Tool(**tool_data)
    executor = Executor(tool=tool, params={})
    result = executor.execute(work_dir=tmp_path)
    
    assert result["validation"]["success"] is False
    stderr_checks = [r for r in result["validation"]["details"] if r["rule"] == "stderr_not_contains"]
    fatal_check = next(r for r in stderr_checks if r["pattern"] == "FATAL")
    error_check = next(r for r in stderr_checks if r["pattern"] == "ERROR")
    assert fatal_check["success"] is False
    assert error_check["success"] is False

def test_post_exec_error_handling(tmp_path: Path):
    """Test error handling in post_exec functions."""
    
    # Test find_onnx_file with no ONNX files
    tool_data = {
        "name": "no-onnx-tool",
        "command_template": "echo 'no onnx files'",
        "post_exec": {
            "outputs": {
                "onnx_file": "find_onnx_file(dir='{{ output_dir }}')"
            }
        }
    }
    tool = Tool(**tool_data)
    executor = Executor(tool=tool, params={"output_dir": "empty_dir"})
    
    with pytest.raises(RuntimeError) as excinfo:
        executor.execute(work_dir=tmp_path)
    
    assert "Failed to resolve post_exec output" in str(excinfo.value)
    assert "No ONNX file found" in str(excinfo.value)


class TestEnhancedFileSearchFunctions:
    """Test the enhanced file search functions."""
    
    def test_find_latest_file_basic(self, tmp_path: Path):
        """Test find_latest_file with basic pattern."""
        # Create test files with different timestamps
        file1 = tmp_path / "test1.txt"
        file2 = tmp_path / "test2.txt"
        
        file1.write_text("content1")
        file2.write_text("content2")
        
        # Modify timestamps to ensure file2 is newer
        import time
        time.sleep(0.1)
        file2.touch()
        
        result = find_latest_file(str(tmp_path), "*.txt")
        assert result == str(file2)
    
    def test_find_latest_file_recursive(self, tmp_path: Path):
        """Test find_latest_file with recursive pattern."""
        # Create nested directory structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        
        file1 = tmp_path / "test1.txt"
        file2 = subdir / "test2.txt"
        
        file1.write_text("content1")
        file2.write_text("content2")
        
        # Make file2 newer
        import time
        time.sleep(0.1)
        file2.touch()
        
        result = find_latest_file(str(tmp_path), "**/*.txt")
        assert result == str(file2)
    
    def test_find_latest_file_not_found(self, tmp_path: Path):
        """Test find_latest_file raises error when no files found."""
        with pytest.raises(FileNotFoundError) as excinfo:
            find_latest_file(str(tmp_path), "*.nonexistent")
        assert "No file found for pattern" in str(excinfo.value)
    
    def test_find_onnx_file_default_pattern(self, tmp_path: Path):
        """Test find_onnx_file with default pattern."""
        # Create ONNX file in nested structure
        model_dir = tmp_path / "Conv_testcase_98bd3f" / "resources"
        model_dir.mkdir(parents=True)
        onnx_file = model_dir / "Conv_testcase_98bd3f.onnx"
        onnx_file.write_text("fake onnx content")
        
        result = find_onnx_file(str(tmp_path))
        assert result == str(onnx_file)
    
    def test_find_onnx_file_custom_pattern(self, tmp_path: Path):
        """Test find_onnx_file with custom pattern."""
        onnx_file = tmp_path / "model.onnx"
        onnx_file.write_text("fake onnx content")
        
        result = find_onnx_file(str(tmp_path), "*.onnx")
        assert result == str(onnx_file)
    
    def test_find_onnx_file_multiple_files(self, tmp_path: Path):
        """Test find_onnx_file returns most recent when multiple files exist."""
        onnx1 = tmp_path / "model1.onnx"
        onnx2 = tmp_path / "model2.onnx"
        
        onnx1.write_text("content1")
        onnx2.write_text("content2")
        
        # Make onnx2 newer
        import time
        time.sleep(0.1)
        onnx2.touch()
        
        result = find_onnx_file(str(tmp_path), "*.onnx")
        assert result == str(onnx2)
    
    def test_find_onnx_file_not_found(self, tmp_path: Path):
        """Test find_onnx_file raises error when no ONNX files found."""
        with pytest.raises(FileNotFoundError) as excinfo:
            find_onnx_file(str(tmp_path))
        assert "No ONNX file found" in str(excinfo.value)
    
    def test_find_onnx_dir(self, tmp_path: Path):
        """Test find_onnx_dir returns directory containing ONNX file."""
        model_dir = tmp_path / "Conv_testcase_98bd3f" / "resources"
        model_dir.mkdir(parents=True)
        onnx_file = model_dir / "Conv_testcase_98bd3f.onnx"
        onnx_file.write_text("fake onnx content")
        
        result = find_onnx_dir(str(tmp_path))
        assert result == str(model_dir)
    
    def test_check_file_exists_true(self, tmp_path: Path):
        """Test check_file_exists returns True for existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        assert check_file_exists(str(test_file)) is True
    
    def test_check_file_exists_false(self, tmp_path: Path):
        """Test check_file_exists returns False for non-existing file."""
        test_file = tmp_path / "nonexistent.txt"
        assert check_file_exists(str(test_file)) is False


class TestEnhancedExecutorValidation:
    """Test the enhanced executor validation functionality."""
    
    def test_validation_exit_code_success(self, tmp_path: Path):
        """Test validation passes when exit code matches expected."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'success'",
            "validation": {
                "exit_code": 0
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is True
        assert any(r["rule"] == "exit_code" and r["success"] for r in result["validation"]["details"])
    
    def test_validation_exit_code_failure(self, tmp_path: Path):
        """Test validation fails when exit code doesn't match expected."""
        tool_data = {
            "name": "test-tool",
            "command_template": "exit 1",
            "validation": {
                "exit_code": 0
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is False
        exit_code_result = next(r for r in result["validation"]["details"] if r["rule"] == "exit_code")
        assert exit_code_result["success"] is False
        assert exit_code_result["expected"] == 0
        assert exit_code_result["actual"] == 1
    
    def test_validation_stdout_contains_success(self, tmp_path: Path):
        """Test validation passes when stdout contains expected patterns."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'Hello World'",
            "validation": {
                "stdout_contains": ["Hello", "World"]
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is True
        stdout_results = [r for r in result["validation"]["details"] if r["rule"] == "stdout_contains"]
        assert len(stdout_results) == 2
        assert all(r["success"] for r in stdout_results)
    
    def test_validation_stdout_contains_failure(self, tmp_path: Path):
        """Test validation fails when stdout doesn't contain expected patterns."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'Hello'",
            "validation": {
                "stdout_contains": ["Hello", "Missing"]
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is False
        stdout_results = [r for r in result["validation"]["details"] if r["rule"] == "stdout_contains"]
        hello_result = next(r for r in stdout_results if r["pattern"] == "Hello")
        missing_result = next(r for r in stdout_results if r["pattern"] == "Missing")
        
        assert hello_result["success"] is True
        assert missing_result["success"] is False
    
    def test_validation_stderr_not_contains_success(self, tmp_path: Path):
        """Test validation passes when stderr doesn't contain forbidden patterns."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'normal output'",
            "validation": {
                "stderr_not_contains": ["ERROR", "FATAL"]
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is True
        stderr_results = [r for r in result["validation"]["details"] if r["rule"] == "stderr_not_contains"]
        assert len(stderr_results) == 2
        assert all(r["success"] for r in stderr_results)
    
    def test_validation_stderr_not_contains_failure(self, tmp_path: Path):
        """Test validation fails when stderr contains forbidden patterns."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'ERROR: something went wrong' >&2",
            "validation": {
                "stderr_not_contains": ["ERROR", "FATAL"]
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is False
        stderr_results = [r for r in result["validation"]["details"] if r["rule"] == "stderr_not_contains"]
        error_result = next(r for r in stderr_results if r["pattern"] == "ERROR")
        fatal_result = next(r for r in stderr_results if r["pattern"] == "FATAL")
        
        assert error_result["success"] is False
        assert fatal_result["success"] is True
    
    def test_validation_output_files_exist_success(self, tmp_path: Path):
        """Test validation passes when expected output files exist."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'content' > {{ output_file }}",
            "validation": {
                "output_files_exist": ["{{ output_file }}"]
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={"output_file": "test_output.txt"})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is True
        file_results = [r for r in result["validation"]["details"] if r["rule"] == "output_files_exist"]
        assert len(file_results) == 1
        assert file_results[0]["success"] is True
    
    def test_validation_output_files_exist_glob_pattern(self, tmp_path: Path):
        """Test validation with glob patterns for output files."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'content1' > file1.txt && echo 'content2' > file2.txt",
            "validation": {
                "output_files_exist": ["*.txt"]
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is True
        file_results = [r for r in result["validation"]["details"] if r["rule"] == "output_files_exist"]
        assert len(file_results) == 1
        assert file_results[0]["success"] is True
        assert len(file_results[0]["found_files"]) == 2
    
    def test_validation_output_files_exist_failure(self, tmp_path: Path):
        """Test validation fails when expected output files don't exist."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'no file created'",
            "validation": {
                "output_files_exist": ["nonexistent.txt"]
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is False
        file_results = [r for r in result["validation"]["details"] if r["rule"] == "output_files_exist"]
        assert len(file_results) == 1
        assert file_results[0]["success"] is False
    
    def test_validation_success_pattern(self, tmp_path: Path):
        """Test validation with success pattern matching."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'Operation completed successfully'",
            "success_pattern": "completed successfully"
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is True
        pattern_results = [r for r in result["validation"]["details"] if r["rule"] == "success_pattern"]
        assert len(pattern_results) == 1
        assert pattern_results[0]["success"] is True
    
    def test_validation_failure_pattern(self, tmp_path: Path):
        """Test validation with failure pattern matching."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'FATAL ERROR occurred' >&2 && exit 1",
            "failure_pattern": "FATAL ERROR"
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is False
        pattern_results = [r for r in result["validation"]["details"] if r["rule"] == "failure_pattern"]
        assert len(pattern_results) == 1
        assert pattern_results[0]["success"] is False
    
    def test_validation_combined_rules(self, tmp_path: Path):
        """Test validation with multiple rules combined."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'Success: file created' && echo 'content' > output.txt",
            "validation": {
                "exit_code": 0,
                "stdout_contains": ["Success"],
                "output_files_exist": ["output.txt"]
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is True
        assert len(result["validation"]["details"]) == 3
        assert all(r["success"] for r in result["validation"]["details"])
    
    def test_validation_no_rules(self, tmp_path: Path):
        """Test validation when no rules are defined."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'no validation'"
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert result["validation"]["success"] is True
        assert result["validation"]["details"] == "No validation rules defined"


class TestEnhancedPostExecFunctions:
    """Test the enhanced post_exec functions integration."""
    
    def test_post_exec_find_onnx_file(self, tmp_path: Path):
        """Test post_exec integration with find_onnx_file function."""
        # Create ONNX file structure
        model_dir = tmp_path / "outputs" / "Conv_testcase_98bd3f" / "resources"
        model_dir.mkdir(parents=True)
        onnx_file = model_dir / "Conv_testcase_98bd3f.onnx"
        onnx_file.write_text("fake onnx content")
        
        tool_data = {
            "name": "onnx-tool",
            "command_template": "echo 'ONNX file generated'",
            "post_exec": {
                "outputs": {
                    "onnx_file": "find_onnx_file(dir='{{ output_dir }}')"
                }
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={"output_dir": "outputs"})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert "onnx_file" in result["outputs"]
        assert result["outputs"]["onnx_file"] == str(onnx_file)
    
    def test_post_exec_find_onnx_dir(self, tmp_path: Path):
        """Test post_exec integration with find_onnx_dir function."""
        # Create ONNX file structure
        model_dir = tmp_path / "outputs" / "Conv_testcase_98bd3f" / "resources"
        model_dir.mkdir(parents=True)
        onnx_file = model_dir / "Conv_testcase_98bd3f.onnx"
        onnx_file.write_text("fake onnx content")
        
        tool_data = {
            "name": "onnx-tool",
            "command_template": "echo 'ONNX file generated'",
            "post_exec": {
                "outputs": {
                    "onnx_dir": "find_onnx_dir(dir='{{ output_dir }}')"
                }
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={"output_dir": "outputs"})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert "onnx_dir" in result["outputs"]
        assert result["outputs"]["onnx_dir"] == str(model_dir)
    
    def test_post_exec_find_latest_file(self, tmp_path: Path):
        """Test post_exec integration with find_latest_file function."""
        # Create multiple files
        outputs_dir = tmp_path / "outputs"
        outputs_dir.mkdir()
        
        file1 = outputs_dir / "model1.onnx"
        file2 = outputs_dir / "model2.onnx"
        
        file1.write_text("content1")
        file2.write_text("content2")
        
        # Make file2 newer
        import time
        time.sleep(0.1)
        file2.touch()
        
        tool_data = {
            "name": "model-tool",
            "command_template": "echo 'Models generated'",
            "post_exec": {
                "outputs": {
                    "latest_model": "find_latest_file(dir='{{ output_dir }}', pattern='*.onnx')"
                }
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={"output_dir": "outputs"})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert "latest_model" in result["outputs"]
        assert result["outputs"]["latest_model"] == str(file2)
    
    def test_post_exec_check_file_exists(self, tmp_path: Path):
        """Test post_exec integration with check_file_exists function."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        tool_data = {
            "name": "check-tool",
            "command_template": "echo 'File check'",
            "post_exec": {
                "outputs": {
                    "file_exists": "check_file_exists(path='{{ file_path }}')"
                }
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={"file_path": str(test_file)})
        
        result = executor.execute(work_dir=tmp_path)
        
        assert "file_exists" in result["outputs"]
        assert result["outputs"]["file_exists"] is True