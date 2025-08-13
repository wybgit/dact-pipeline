import pytest
import yaml
import shutil
from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Environment
from pytest_html import extras as pytest_html_extras
from dact.models import CaseFile, Scenario, DataDrivenCase
from dact.tool_loader import load_tools_from_directory
from dact.scenario_loader import load_scenarios_from_directory
from dact.executor import Executor
from dact.dependency_resolver import DependencyResolver
from dact.validation_engine import ValidationEngine
from dact.data_providers import load_test_data
from dact.logger import log

TOOL_DIRECTORY = "tools"
SCENARIO_DIRECTORY = "scenarios"

def pytest_collect_file(parent, file_path):
    if hasattr(file_path, 'suffix'):  # pathlib.Path
        if file_path.suffix == ".yml" and file_path.name.endswith(".case.yml"):
            return CaseYAMLFile.from_parent(parent, path=file_path)
    elif hasattr(file_path, 'ext'):  # py.path.local (legacy)
        if file_path.ext == ".yml" and file_path.basename.endswith(".case.yml"):
            return CaseYAMLFile.from_parent(parent, path=file_path)

class CaseYAMLFile(pytest.File):
    def collect(self):
        project_root = self.config.rootpath
        tool_dir = project_root / TOOL_DIRECTORY
        scenario_dir = project_root / SCENARIO_DIRECTORY
        
        self.tools = load_tools_from_directory(str(tool_dir))
        # Load scenarios from default and examples for backward compatibility
        scenarios_main = load_scenarios_from_directory(str(scenario_dir))
        scenarios_examples = load_scenarios_from_directory(str(project_root / "examples" / "scenarios"))
        merged = scenarios_main.copy()
        merged.update(scenarios_examples)
        self.scenarios = merged

        with open(self.fspath, 'r') as f:
            raw_data = yaml.safe_load(f)
        
        case_file = CaseFile(**raw_data)

        # Collect regular test cases
        for case in case_file.cases:
            # Apply common_params to case params
            merged_params = case_file.common_params.copy()
            merged_params.update(case.params)
            case.params = merged_params
            
            yield TestCaseItem.from_parent(self, name=case.name, case=case, tools=self.tools, scenarios=self.scenarios)
        
        # Collect data-driven test cases
        for data_driven_case in case_file.data_driven_cases:
            try:
                test_data = load_test_data(data_driven_case.data_source)
                
                # Apply data filter if specified
                if data_driven_case.data_filter:
                    test_data = self._filter_test_data(test_data, data_driven_case.data_filter)
                
                for i, data_row in enumerate(test_data):
                    # Apply data transformations if specified
                    if data_driven_case.data_transform:
                        data_row = self._transform_data_row(data_row, data_driven_case.data_transform)
                    
                    # Generate case name using template or default
                    if data_driven_case.name_template:
                        case_name = self._render_case_name(data_driven_case.name_template, data_row, i)
                    else:
                        case_name = f"{data_driven_case.template.name}_{i}"
                    
                    # Create a new case instance for each data row
                    case = data_driven_case.template.copy(deep=True)
                    case.name = case_name
                    
                    # Apply parameter mapping
                    mapped_params = self._apply_parameter_mapping(
                        data_row, 
                        data_driven_case.parameter_mapping
                    )
                    
                    # Merge with existing params and common_params
                    final_params = case_file.common_params.copy()
                    final_params.update(case.params)
                    final_params.update(mapped_params)
                    case.params = final_params
                    
                    yield TestCaseItem.from_parent(
                        self, 
                        name=case_name, 
                        case=case, 
                        tools=self.tools, 
                        scenarios=self.scenarios,
                        data_row=data_row
                    )
                    
            except Exception as e:
                log.error(f"Failed to load data-driven test case {data_driven_case.template.name}: {e}")
                # Create a failing test case to report the error
                error_case = data_driven_case.template.copy(deep=True)
                error_case.name = f"{data_driven_case.template.name}_data_load_error"
                yield TestCaseItem.from_parent(
                    self, 
                    name=error_case.name, 
                    case=error_case, 
                    tools=self.tools, 
                    scenarios=self.scenarios,
                    data_load_error=str(e)
                )
    
    def _apply_parameter_mapping(self, data_row: dict, parameter_mapping: dict) -> dict:
        """Apply parameter mapping from data row to case parameters."""
        mapped_params = {}
        
        if not parameter_mapping:
            # If no mapping specified, use data row keys directly
            return data_row
        
        for param_path, data_key in parameter_mapping.items():
            if data_key in data_row:
                # Support nested parameter paths like "step1.param1"
                if '.' in param_path:
                    parts = param_path.split('.')
                    current = mapped_params
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = data_row[data_key]
                else:
                    mapped_params[param_path] = data_row[data_key]
        
        return mapped_params
    
    def _filter_test_data(self, test_data: List[dict], filter_criteria: Dict[str, Any]) -> List[dict]:
        """Filter test data based on criteria."""
        filtered_data = []
        
        for data_row in test_data:
            include_row = True
            
            for key, expected_value in filter_criteria.items():
                if key not in data_row:
                    include_row = False
                    break
                
                actual_value = data_row[key]
                
                # Support different filter operations
                if isinstance(expected_value, dict):
                    # Complex filter operations like {"$gt": 10, "$lt": 100}
                    for op, value in expected_value.items():
                        if op == "$gt" and not (actual_value > value):
                            include_row = False
                            break
                        elif op == "$lt" and not (actual_value < value):
                            include_row = False
                            break
                        elif op == "$gte" and not (actual_value >= value):
                            include_row = False
                            break
                        elif op == "$lte" and not (actual_value <= value):
                            include_row = False
                            break
                        elif op == "$ne" and not (actual_value != value):
                            include_row = False
                            break
                        elif op == "$in" and actual_value not in value:
                            include_row = False
                            break
                        elif op == "$nin" and actual_value in value:
                            include_row = False
                            break
                else:
                    # Simple equality check
                    if actual_value != expected_value:
                        include_row = False
                        break
            
            if include_row:
                filtered_data.append(data_row)
        
        return filtered_data
    
    def _transform_data_row(self, data_row: dict, transformations: Dict[str, str]) -> dict:
        """Apply transformations to data row."""
        transformed_row = data_row.copy()
        
        for target_key, expression in transformations.items():
            try:
                # Simple expression evaluation (can be extended with more complex logic)
                if expression.startswith("int("):
                    # Convert to integer: int(source_key)
                    source_key = expression[4:-1]
                    if source_key in data_row:
                        transformed_row[target_key] = int(data_row[source_key])
                elif expression.startswith("float("):
                    # Convert to float: float(source_key)
                    source_key = expression[6:-1]
                    if source_key in data_row:
                        transformed_row[target_key] = float(data_row[source_key])
                elif expression.startswith("str("):
                    # Convert to string: str(source_key)
                    source_key = expression[4:-1]
                    if source_key in data_row:
                        transformed_row[target_key] = str(data_row[source_key])
                elif "+" in expression:
                    # Simple arithmetic: key1 + key2
                    parts = expression.split("+")
                    if len(parts) == 2:
                        key1, key2 = parts[0].strip(), parts[1].strip()
                        if key1 in data_row and key2 in data_row:
                            transformed_row[target_key] = data_row[key1] + data_row[key2]
                elif expression in data_row:
                    # Simple key mapping
                    transformed_row[target_key] = data_row[expression]
                else:
                    # Literal value
                    transformed_row[target_key] = expression
            except Exception as e:
                log.warning(f"Failed to apply transformation '{expression}' to '{target_key}': {e}")
        
        return transformed_row
    
    def _render_case_name(self, name_template: str, data_row: dict, index: int) -> str:
        """Render case name using template and data row."""
        try:
            from jinja2 import Environment
            env = Environment()
            template = env.from_string(name_template)
            
            # Provide data row and index as template variables
            context = {
                "data": data_row,
                "index": index,
                **data_row  # Also provide data row keys directly
            }
            
            return template.render(**context)
        except Exception as e:
            log.warning(f"Failed to render case name template '{name_template}': {e}")
            return f"case_{index}"

class TestCaseItem(pytest.Item):
    def __init__(self, *, parent, name, case, tools, scenarios, data_row=None, data_load_error=None, **kwargs):
        super().__init__(name, parent, **kwargs)
        self.case = case
        self.tools = tools
        self.scenarios = scenarios
        self.data_row = data_row  # For data-driven tests
        self.data_load_error = data_load_error  # For data loading errors
        self.validation_engine = ValidationEngine()

    def runtest(self):
        import time
        start_time = time.time()
        
        # Handle data loading errors first
        if self.data_load_error:
            pytest.fail(f"Data loading failed: {self.data_load_error}", pytrace=False)
        
        case_work_dir = self.config.rootpath / "dact_outputs" / self.name
        if case_work_dir.exists():
            shutil.rmtree(case_work_dir)
        case_work_dir.mkdir(parents=True)

        log.info(f"[bold]Running case[/bold]: [yellow]{self.name}[/yellow]")
        
        # Log data row information for data-driven tests
        if self.data_row:
            log.info(f"  Data row: {self.data_row}")

        run_context = {"steps": {}}
        jinja_env = Environment()
        
        # Initialize execution summary
        execution_summary = {
            "start_time": start_time,
            "steps_count": 0,
            "validation_results": [],
            "errors": []
        }
        
        # Execute setup if specified
        if self.case.setup:
            log.info("  Executing setup...")
            self._execute_setup(self.case.setup, case_work_dir)

        try:
            if self.case.scenario:
                scenario = self.scenarios.get(self.case.scenario)
                if not scenario:
                    raise pytest.fail(f"Scenario '{self.case.scenario}' not found.")

                # Validate scenario dependencies
                dependency_resolver = DependencyResolver()
                validation_errors = dependency_resolver.validate_dependencies(scenario)
                if validation_errors:
                    error_msg = "Scenario dependency validation failed:\n" + "\n".join(validation_errors)
                    pytest.fail(error_msg, pytrace=False)

                # Get dependency graph and execution order
                dependency_graph = dependency_resolver.extract_dependencies(scenario)
                log.info(f"Scenario execution order: {dependency_graph.execution_order}")

                # Merge scenario default params with case params
                merged_context = {"case": {"name": self.name}}
                if scenario.default_params:
                    merged_context.update(scenario.default_params)
                
                # Add case-level parameters to context
                if self.case.params:
                    merged_context.update(self.case.params)
                
                run_context = {**merged_context, "steps": {}}

                # Execute steps in dependency order
                for level in dependency_graph.execution_order:
                    for step_name in level:
                        # Find the step definition
                        step = next((s for s in scenario.steps if s.name == step_name), None)
                        if not step:
                            pytest.fail(f"Step '{step_name}' not found in scenario definition.")
                        
                        log.info(f"  -> [bold]Step[/bold]: [blue]{step.name}[/blue]")
                        step_work_dir = case_work_dir / step.name
                        step_work_dir.mkdir()

                        tool = self.tools.get(step.tool)
                        if not tool:
                            raise pytest.fail(f"Tool '{step.tool}' not found for step '{step.name}'.")

                        # Prepare parameters for rendering
                        params_to_render = step.params.copy()
                        
                        # Apply scenario default params
                        if scenario.default_params:
                            for key, value in scenario.default_params.items():
                                if key not in params_to_render:
                                    params_to_render[key] = value
                        
                        # Apply case-specific step parameters
                        if self.case.params and step.name in self.case.params:
                            params_to_render.update(self.case.params[step.name])

                        # Render parameters with current context
                        rendered_params = self._render_parameters(params_to_render, run_context, jinja_env)

                        # Check for debug mode from pytest config
                        debug_mode = self.config.option.capture == 'no'  # -s flag sets capture to 'no'
                        
                        executor = Executor(tool=tool, params=rendered_params)
                        result = executor.execute(work_dir=step_work_dir, debug_mode=debug_mode)

                        # Update run context with step outputs
                        run_context["steps"][step.name] = {"outputs": result["outputs"]}
                        
                        # Update execution summary
                        execution_summary["steps_count"] += 1
                        if result.get("validation"):
                            execution_summary["validation_results"].append({
                                "step": step.name,
                                "validation": result["validation"]
                            })

                        # Check for step failure
                        if result["returncode"] != 0:
                            execution_summary["errors"].append({
                                "step": step.name,
                                "exit_code": result["returncode"],
                                "command": result["command"]
                            })
                            
                            if step.continue_on_failure:
                                log.warning(f"  Step '{step.name}' failed but continuing due to continue_on_failure=True")
                            else:
                                log.error(f"  Step '{step.name}' failed!")
                                pytest.fail(
                                    f"Step '{step.name}' failed with exit code {result['returncode']}.\n"
                                    f"Command: {result['command']}\n"
                                    f"Logs are in: {step_work_dir}",
                                    pytrace=False
                                )
                
                # Execute case-level validations after scenario completion
                if self.case.validation:
                    log.info("  [bold]Case validations[/bold]...")
                    self._execute_validations(case_work_dir, {"returncode": 0, "outputs": run_context.get("steps", {})})
                
                log.info(f"[bold green]Case '{self.name}' finished successfully.[/bold green]")

            elif self.case.tool:
                log.info(f"  -> [bold]Tool[/bold]: [blue]{self.case.tool}[/blue]")
                tool = self.tools.get(self.case.tool)
                if not tool:
                    raise pytest.fail(f"Tool '{self.case.tool}' not found for case '{self.case.name}'.")
                
                params = self.case.params or {}
                # Check for debug mode from pytest config
                debug_mode = self.config.option.capture == 'no'  # -s flag sets capture to 'no'
                
                executor = Executor(tool=tool, params=params)
                result = executor.execute(work_dir=case_work_dir, debug_mode=debug_mode)

                # Execute case-level validations
                if self.case.validation:
                    log.info("  [bold]Case validations[/bold]...")
                    self._execute_validations(case_work_dir, result)
                elif result["returncode"] != 0:
                    log.error(f"  Tool '{self.case.tool}' failed!")
                    pytest.fail(
                        f"Case '{self.name}' failed with exit code {result['returncode']}.\n"
                        f"Command: {result['command']}\n"
                        f"Logs are in: {case_work_dir}",
                        pytrace=False
                    )
                
                log.info(f"[bold green]Case '{self.name}' finished successfully.[/bold green]")
            else:
                raise pytest.fail("Case must have either a 'scenario' or a 'tool'.")
        
        finally:
            # Execute teardown if specified
            if self.case.teardown:
                log.info("  Executing teardown...")
                try:
                    self._execute_teardown(self.case.teardown, case_work_dir)
                except Exception as e:
                    log.warning(f"Teardown failed: {e}")
                    execution_summary["errors"].append({
                        "step": "teardown",
                        "error": str(e)
                    })
            
            # Finalize execution summary
            end_time = time.time()
            execution_summary["end_time"] = end_time
            execution_summary["duration"] = f"{end_time - start_time:.2f}s"
            
            # Store execution summary for HTML report
            self._execution_summary = execution_summary

    def _render_parameters(self, params: dict, context: dict, jinja_env: Environment) -> dict:
        """
        Recursively render parameters using Jinja2 templates.
        
        Supports nested dictionaries and lists.
        """
        rendered_params = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                try:
                    template = jinja_env.from_string(value)
                    rendered_params[key] = template.render(**context)
                except Exception as e:
                    log.error(f"Failed to render parameter '{key}' with value '{value}': {e}")
                    raise pytest.fail(f"Parameter rendering failed for '{key}': {e}", pytrace=False)
            elif isinstance(value, dict):
                rendered_params[key] = self._render_parameters(value, context, jinja_env)
            elif isinstance(value, list):
                rendered_params[key] = [
                    self._render_parameters(item, context, jinja_env) if isinstance(item, dict)
                    else jinja_env.from_string(str(item)).render(**context) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                rendered_params[key] = value
        
        return rendered_params

    def _execute_setup(self, setup_config: dict, work_dir: Path):
        """Execute setup operations before test case."""
        # This can be extended to support various setup operations
        # For now, just log the setup configuration
        log.debug(f"Setup configuration: {setup_config}")
    
    def _execute_teardown(self, teardown_config: dict, work_dir: Path):
        """Execute teardown operations after test case."""
        # This can be extended to support various teardown operations
        # For now, just log the teardown configuration
        log.debug(f"Teardown configuration: {teardown_config}")
    
    def _execute_validations(self, work_dir: Path, execution_result: dict):
        """Execute all validations for the test case."""
        if not self.case.validation:
            return
        
        log.info(f"  Running {len(self.case.validation)} validation(s)...")
        
        validation_results = self.validation_engine.validate_case(
            self.case.validation, 
            execution_result, 
            work_dir
        )
        
        # Check if any validations failed
        failed_validations = [r for r in validation_results if not r.is_valid]
        
        if failed_validations:
            error_messages = []
            for result in failed_validations:
                error_messages.append(f"  - {result.message}")
            
            pytest.fail(
                f"Case '{self.name}' validation failed:\n" + "\n".join(error_messages) + 
                f"\nLogs are in: {work_dir}",
                pytrace=False
            )

    def repr_failure(self, excinfo):
        if isinstance(excinfo.value, pytest.fail.Exception):
            return excinfo.value.args[0]
        return super().repr_failure(excinfo)

    def reportinfo(self):
        return self.fspath, 0, f"case: {self.name}"

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Enhanced hook to add comprehensive information to the pytest-html report.
    """
    outcome = yield
    report = outcome.get_result()
    extra = getattr(report, "extra", [])
    
    if report.when == "call" and hasattr(item, 'case'):
        # Add the path to the temporary log directory to the report
        log_dir = item.config.rootpath / "dact_outputs" / item.name
        
        # Add log directory link
        if log_dir.exists():
            extra.append(pytest_html_extras.url(str(log_dir), name="📁 Log Directory"))
        
        # Add case information
        case_info = []
        case_info.append(f"<h4>Test Case Information</h4>")
        case_info.append(f"<p><strong>Name:</strong> {item.case.name}</p>")
        
        if item.case.description:
            case_info.append(f"<p><strong>Description:</strong> {item.case.description}</p>")
        
        if item.case.tags:
            tags_html = ", ".join([f"<span style='background-color: #e1f5fe; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;'>{tag}</span>" for tag in item.case.tags])
            case_info.append(f"<p><strong>Tags:</strong> {tags_html}</p>")
        
        if item.case.scenario:
            case_info.append(f"<p><strong>Scenario:</strong> {item.case.scenario}</p>")
        elif item.case.tool:
            case_info.append(f"<p><strong>Tool:</strong> {item.case.tool}</p>")
        
        # Add data row information for data-driven tests
        if hasattr(item, 'data_row') and item.data_row:
            case_info.append(f"<h4>Data-Driven Test Data</h4>")
            case_info.append("<table style='border-collapse: collapse; width: 100%;'>")
            case_info.append("<tr style='background-color: #f5f5f5;'><th style='border: 1px solid #ddd; padding: 8px;'>Parameter</th><th style='border: 1px solid #ddd; padding: 8px;'>Value</th></tr>")
            for key, value in item.data_row.items():
                case_info.append(f"<tr><td style='border: 1px solid #ddd; padding: 8px;'>{key}</td><td style='border: 1px solid #ddd; padding: 8px;'>{value}</td></tr>")
            case_info.append("</table>")
        
        # Add parameters information
        if item.case.params:
            case_info.append(f"<h4>Parameters</h4>")
            case_info.append("<table style='border-collapse: collapse; width: 100%;'>")
            case_info.append("<tr style='background-color: #f5f5f5;'><th style='border: 1px solid #ddd; padding: 8px;'>Parameter</th><th style='border: 1px solid #ddd; padding: 8px;'>Value</th></tr>")
            for key, value in item.case.params.items():
                # Handle nested parameters
                if isinstance(value, dict):
                    value_str = "<br>".join([f"&nbsp;&nbsp;{k}: {v}" for k, v in value.items()])
                elif isinstance(value, list):
                    value_str = "<br>".join([f"&nbsp;&nbsp;- {v}" for v in value])
                else:
                    value_str = str(value)
                case_info.append(f"<tr><td style='border: 1px solid #ddd; padding: 8px;'>{key}</td><td style='border: 1px solid #ddd; padding: 8px;'>{value_str}</td></tr>")
            case_info.append("</table>")
        
        # Add case information as HTML extra
        extra.append(pytest_html_extras.html("".join(case_info)))
        
        # Add log file links if they exist
        log_files = []
        if log_dir.exists():
            # Look for step directories and their log files
            for step_dir in log_dir.iterdir():
                if step_dir.is_dir():
                    stdout_log = step_dir / "stdout.log"
                    stderr_log = step_dir / "stderr.log"
                    
                    if stdout_log.exists():
                        log_files.append(f"<a href='file://{stdout_log}' target='_blank'>📄 {step_dir.name}/stdout.log</a>")
                    if stderr_log.exists():
                        log_files.append(f"<a href='file://{stderr_log}' target='_blank'>📄 {step_dir.name}/stderr.log</a>")
            
            # Look for case-level log files
            case_stdout = log_dir / "stdout.log"
            case_stderr = log_dir / "stderr.log"
            if case_stdout.exists():
                log_files.append(f"<a href='file://{case_stdout}' target='_blank'>📄 stdout.log</a>")
            if case_stderr.exists():
                log_files.append(f"<a href='file://{case_stderr}' target='_blank'>📄 stderr.log</a>")
        
        if log_files:
            log_files_html = f"<h4>Log Files</h4><p>" + " | ".join(log_files) + "</p>"
            extra.append(pytest_html_extras.html(log_files_html))
        
        # Add execution summary if available
        if hasattr(item, '_execution_summary'):
            summary = item._execution_summary
            summary_html = []
            summary_html.append("<h4>Execution Summary</h4>")
            summary_html.append(f"<p><strong>Duration:</strong> {summary.get('duration', 'N/A')}</p>")
            summary_html.append(f"<p><strong>Steps Executed:</strong> {summary.get('steps_count', 'N/A')}</p>")
            if summary.get('validation_results'):
                summary_html.append(f"<p><strong>Validations:</strong> {len(summary['validation_results'])} checks</p>")
            
            extra.append(pytest_html_extras.html("".join(summary_html)))
        
        if hasattr(report, 'extras'):
            report.extras = extra
        else:
            # Fallback for older pytest-html versions
            report.extra = extra

def pytest_html_report_title(report):
    """Customize the HTML report title."""
    report.title = "DACT Pipeline Test Report"

def pytest_html_results_summary(prefix, summary, postfix):
    """Customize the results summary in HTML report."""
    prefix.extend([
        "<h2>DACT Pipeline Test Results</h2>",
        "<p>This report contains the results of DACT pipeline tests including tool executions, scenario orchestrations, and validations.</p>"
    ])

@pytest.hookimpl(hookwrapper=True)
def pytest_html_results_table_header(cells):
    """Customize the results table header."""
    outcome = yield
    cells.insert(2, "<th>Type</th>")
    cells.insert(3, "<th>Duration</th>")

@pytest.hookimpl(hookwrapper=True) 
def pytest_html_results_table_row(report, cells):
    """Customize the results table rows."""
    outcome = yield
    
    # Add test type information
    test_type = "Unknown"
    if hasattr(report, 'nodeid'):
        if '.case.yml' in report.nodeid:
            test_type = "Case"
        elif 'scenario' in report.nodeid.lower():
            test_type = "Scenario"
        elif 'tool' in report.nodeid.lower():
            test_type = "Tool"
    
    cells.insert(2, f"<td>{test_type}</td>")
    
    # Add duration information
    duration = getattr(report, 'duration', 0)
    duration_str = f"{duration:.2f}s" if duration else "N/A"
    cells.insert(3, f"<td>{duration_str}</td>")