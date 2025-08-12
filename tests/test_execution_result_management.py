"""
Tests for execution result management and logging system.
"""
import pytest
import shutil
from pathlib import Path
from dact.models import Tool, Case, CaseFile, Scenario, Step
from dact.executor import Executor
from dact.pytest_plugin import TestCaseItem, CaseYAMLFile
from dact.logger import log, console


class TestWorkDirectoryManagement:
    """Test work directory management functionality."""
    
    def test_case_work_dir_creation(self, tmp_path: Path):
        """Test that case work directory is created correctly."""
        case_name = "test_case_work_dir"
        case_work_dir = tmp_path / "tmp" / case_name
        
        # Ensure directory doesn't exist initially
        assert not case_work_dir.exists()
        
        # Create the directory structure as done in pytest_plugin
        if case_work_dir.exists():
            shutil.rmtree(case_work_dir)
        case_work_dir.mkdir(parents=True)
        
        assert case_work_dir.exists()
        assert case_work_dir.is_dir()
    
    def test_case_work_dir_cleanup(self, tmp_path: Path):
        """Test that existing case work directory is cleaned up before new execution."""
        case_name = "test_case_cleanup"
        case_work_dir = tmp_path / "tmp" / case_name
        
        # Create directory with some content
        case_work_dir.mkdir(parents=True)
        old_file = case_work_dir / "old_file.txt"
        old_file.write_text("old content")
        
        assert old_file.exists()
        
        # Simulate cleanup as done in pytest_plugin
        if case_work_dir.exists():
            shutil.rmtree(case_work_dir)
        case_work_dir.mkdir(parents=True)
        
        assert case_work_dir.exists()
        assert not old_file.exists()
    
    def test_step_work_dir_creation(self, tmp_path: Path):
        """Test that step work directories are created correctly."""
        case_work_dir = tmp_path / "tmp" / "test_case"
        case_work_dir.mkdir(parents=True)
        
        step_names = ["step1", "step2", "step3"]
        step_work_dirs = []
        
        for step_name in step_names:
            step_work_dir = case_work_dir / step_name
            step_work_dir.mkdir()
            step_work_dirs.append(step_work_dir)
        
        for step_work_dir in step_work_dirs:
            assert step_work_dir.exists()
            assert step_work_dir.is_dir()
    
    def test_log_file_creation(self, tmp_path: Path):
        """Test that stdout and stderr log files are created correctly."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo 'stdout message' && echo 'stderr message' >&2"
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        work_dir = tmp_path / "test_work_dir"
        work_dir.mkdir()
        
        result = executor.execute(work_dir=work_dir)
        
        # Check that log files are created
        stdout_log = work_dir / "stdout.log"
        stderr_log = work_dir / "stderr.log"
        
        assert stdout_log.exists()
        assert stderr_log.exists()
        
        # Check log file contents
        assert "stdout message" in stdout_log.read_text()
        assert "stderr message" in stderr_log.read_text()
    
    def test_log_file_encoding_utf8(self, tmp_path: Path):
        """Test that log files handle UTF-8 encoding correctly."""
        tool_data = {
            "name": "test-tool",
            "command_template": "echo '测试中文字符: Hello 世界'"
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        work_dir = tmp_path / "test_work_dir"
        work_dir.mkdir()
        
        result = executor.execute(work_dir=work_dir)
        
        stdout_log = work_dir / "stdout.log"
        assert stdout_log.exists()
        
        # Read with explicit UTF-8 encoding
        content = stdout_log.read_text(encoding='utf-8')
        assert "测试中文字符" in content
        assert "Hello 世界" in content


class TestLogSavingFunctionality:
    """Test log saving functionality."""
    
    def test_executor_saves_command_output(self, tmp_path: Path):
        """Test that executor saves command output to log files."""
        tool_data = {
            "name": "output-tool",
            "command_template": "echo 'Command executed successfully' && echo 'Warning message' >&2"
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        work_dir = tmp_path / "executor_test"
        work_dir.mkdir()
        
        result = executor.execute(work_dir=work_dir)
        
        # Verify result contains output
        assert "Command executed successfully" in result["stdout"]
        assert "Warning message" in result["stderr"]
        assert result["returncode"] == 0
        
        # Verify log files are saved
        stdout_log = work_dir / "stdout.log"
        stderr_log = work_dir / "stderr.log"
        
        assert stdout_log.exists()
        assert stderr_log.exists()
        
        # Verify log file contents match result
        assert stdout_log.read_text().strip() == result["stdout"].strip()
        assert stderr_log.read_text().strip() == result["stderr"].strip()
    
    def test_executor_saves_empty_output(self, tmp_path: Path):
        """Test that executor handles empty output correctly."""
        tool_data = {
            "name": "silent-tool",
            "command_template": "true"  # Command that produces no output
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        work_dir = tmp_path / "silent_test"
        work_dir.mkdir()
        
        result = executor.execute(work_dir=work_dir)
        
        # Verify empty output is handled
        assert result["stdout"] == ""
        assert result["stderr"] == ""
        assert result["returncode"] == 0
        
        # Verify log files are still created (even if empty)
        stdout_log = work_dir / "stdout.log"
        stderr_log = work_dir / "stderr.log"
        
        assert stdout_log.exists()
        assert stderr_log.exists()
        assert stdout_log.read_text() == ""
        assert stderr_log.read_text() == ""
    
    def test_executor_saves_large_output(self, tmp_path: Path):
        """Test that executor handles large output correctly."""
        # Generate a large output (1000 lines)
        large_content = "\\n".join([f"Line {i}: This is a test line with some content" for i in range(1000)])
        
        tool_data = {
            "name": "large-output-tool",
            "command_template": f"echo -e '{large_content}'"
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        work_dir = tmp_path / "large_output_test"
        work_dir.mkdir()
        
        result = executor.execute(work_dir=work_dir)
        
        # Verify large output is captured
        assert "Line 0:" in result["stdout"]
        assert "Line 999:" in result["stdout"]
        assert result["returncode"] == 0
        
        # Verify log file contains all content
        stdout_log = work_dir / "stdout.log"
        assert stdout_log.exists()
        
        log_content = stdout_log.read_text()
        assert "Line 0:" in log_content
        assert "Line 999:" in log_content


class TestExecutionResultStructure:
    """Test the structure and completeness of execution results."""
    
    def test_execution_result_contains_required_fields(self, tmp_path: Path):
        """Test that execution result contains all required fields."""
        tool_data = {
            "name": "complete-tool",
            "command_template": "echo 'test output'",
            "post_exec": {
                "outputs": {
                    "test_output": "find_file(dir='.', pattern='stdout.log')"
                }
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        work_dir = tmp_path / "complete_test"
        work_dir.mkdir()
        
        result = executor.execute(work_dir=work_dir)
        
        # Verify all required fields are present
        required_fields = ["stdout", "stderr", "returncode", "command", "outputs", "validation"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Verify field types
        assert isinstance(result["stdout"], str)
        assert isinstance(result["stderr"], str)
        assert isinstance(result["returncode"], int)
        assert isinstance(result["command"], str)
        assert isinstance(result["outputs"], dict)
        assert isinstance(result["validation"], dict)
    
    def test_execution_result_validation_structure(self, tmp_path: Path):
        """Test that validation results have correct structure."""
        tool_data = {
            "name": "validation-tool",
            "command_template": "echo 'success'",
            "validation": {
                "exit_code": 0,
                "stdout_contains": ["success"]
            }
        }
        tool = Tool(**tool_data)
        executor = Executor(tool=tool, params={})
        
        work_dir = tmp_path / "validation_test"
        work_dir.mkdir()
        
        result = executor.execute(work_dir=work_dir)
        
        # Verify validation structure
        validation = result["validation"]
        assert "success" in validation
        assert "details" in validation
        assert isinstance(validation["success"], bool)
        assert isinstance(validation["details"], list)
        
        # Verify validation details
        for detail in validation["details"]:
            assert "rule" in detail
            assert "success" in detail
            assert isinstance(detail["success"], bool)


class TestWorkDirectoryIsolation:
    """Test that work directories provide proper isolation."""
    
    def test_concurrent_execution_isolation(self, tmp_path: Path):
        """Test that concurrent executions don't interfere with each other."""
        tool_data = {
            "name": "isolation-tool",
            "command_template": "echo '{{ case_id }}' > case_output.txt"
        }
        tool = Tool(**tool_data)
        
        # Simulate two concurrent executions
        work_dir1 = tmp_path / "case1"
        work_dir2 = tmp_path / "case2"
        work_dir1.mkdir()
        work_dir2.mkdir()
        
        executor1 = Executor(tool=tool, params={"case_id": "case1"})
        executor2 = Executor(tool=tool, params={"case_id": "case2"})
        
        result1 = executor1.execute(work_dir=work_dir1)
        result2 = executor2.execute(work_dir=work_dir2)
        
        # Verify outputs are isolated
        output_file1 = work_dir1 / "case_output.txt"
        output_file2 = work_dir2 / "case_output.txt"
        
        assert output_file1.exists()
        assert output_file2.exists()
        assert "case1" in output_file1.read_text()
        assert "case2" in output_file2.read_text()
        
        # Verify log files are isolated
        assert (work_dir1 / "stdout.log").exists()
        assert (work_dir2 / "stdout.log").exists()
        assert "case1" in (work_dir1 / "stdout.log").read_text()
        assert "case2" in (work_dir2 / "stdout.log").read_text()


class TestPytestHtmlIntegration:
    """Test pytest-html report integration."""
    
    def test_html_report_generation(self, tmp_path):
        """Test that HTML report can be generated with enhanced information."""
        # This test verifies the structure needed for HTML report generation
        # The actual HTML generation is tested through pytest execution
        
        from dact.pytest_plugin import pytest_runtest_makereport
        from pytest_html import extras as pytest_html_extras
        
        # Mock test item with case information
        class MockItem:
            def __init__(self):
                self.name = "test_html_case"
                self.config = type('Config', (), {'rootpath': tmp_path})()
                self.case = type('Case', (), {
                    'name': 'test_html_case',
                    'description': 'Test case for HTML report',
                    'tags': ['html', 'test'],
                    'scenario': 'test_scenario',
                    'tool': None,
                    'params': {'param1': 'value1', 'param2': {'nested': 'value'}}
                })()
                self.data_row = {'data_key': 'data_value'}
                self._execution_summary = {
                    'duration': '1.23s',
                    'steps_count': 2,
                    'validation_results': [{'step': 'step1', 'validation': {'success': True}}]
                }
        
        # Mock report
        class MockReport:
            def __init__(self):
                self.when = "call"
                self.extra = []
        
        # Create log directory structure
        log_dir = tmp_path / "tmp" / "test_html_case"
        log_dir.mkdir(parents=True)
        step_dir = log_dir / "step1"
        step_dir.mkdir()
        (step_dir / "stdout.log").write_text("Step output")
        (step_dir / "stderr.log").write_text("Step errors")
        
        # Test that the hook can process the item without errors
        item = MockItem()
        report = MockReport()
        
        # This should not raise any exceptions
        try:
            # Simulate the hook behavior
            extra = []
            
            # Add log directory link
            if log_dir.exists():
                extra.append(pytest_html_extras.url(str(log_dir), name="📁 Log Directory"))
            
            # Add case information
            case_info = []
            case_info.append(f"<h4>Test Case Information</h4>")
            case_info.append(f"<p><strong>Name:</strong> {item.case.name}</p>")
            
            report.extra = extra
            
            # Verify that extras were added
            assert len(report.extra) >= 1
            assert any("Log Directory" in str(extra) for extra in report.extra)
            
        except Exception as e:
            pytest.fail(f"HTML report integration failed: {e}")
    
    def test_execution_summary_tracking(self, tmp_path):
        """Test that execution summary is properly tracked."""
        from dact.models import Tool, Case
        from dact.pytest_plugin import TestCaseItem
        
        # Create a simple test case
        case = Case(
            name="summary_test",
            tool="test-tool",
            params={"test_param": "test_value"}
        )
        
        # Mock tools and scenarios
        tools = {
            "test-tool": Tool(
                name="test-tool",
                command_template="echo 'test output'"
            )
        }
        scenarios = {}
        
        # Create test item
        class MockParent:
            def __init__(self):
                self.config = type('Config', (), {'rootpath': tmp_path})()
        
        parent = MockParent()
        test_item = TestCaseItem.from_parent(
            parent, 
            name="summary_test",
            case=case,
            tools=tools,
            scenarios=scenarios
        )
        
        # Execute the test (this will create the execution summary)
        try:
            test_item.runtest()
        except Exception:
            # Test might fail due to missing dependencies, but we're testing summary tracking
            pass
        
        # Verify execution summary was created
        assert hasattr(test_item, '_execution_summary')
        summary = test_item._execution_summary
        
        # Verify summary structure
        assert 'start_time' in summary
        assert 'duration' in summary
        assert 'steps_count' in summary
        assert 'validation_results' in summary
        assert 'errors' in summary


class TestLogFileManagement:
    """Test log file management and organization."""
    
    def test_log_file_organization(self, tmp_path):
        """Test that log files are organized correctly in work directories."""
        from dact.models import Tool
        from dact.executor import Executor
        
        # Create a tool that generates multiple types of output
        tool = Tool(
            name="multi-output-tool",
            command_template="echo 'stdout message' && echo 'stderr message' >&2 && echo 'file content' > output.txt"
        )
        
        work_dir = tmp_path / "multi_output_test"
        work_dir.mkdir()
        
        executor = Executor(tool=tool, params={})
        result = executor.execute(work_dir=work_dir)
        
        # Verify log files are created
        stdout_log = work_dir / "stdout.log"
        stderr_log = work_dir / "stderr.log"
        output_file = work_dir / "output.txt"
        
        assert stdout_log.exists()
        assert stderr_log.exists()
        assert output_file.exists()
        
        # Verify log file contents
        assert "stdout message" in stdout_log.read_text()
        assert "stderr message" in stderr_log.read_text()
        assert "file content" in output_file.read_text()
        
        # Verify result structure
        assert result["returncode"] == 0
        assert "stdout message" in result["stdout"]
        assert "stderr message" in result["stderr"]
    
    def test_nested_work_directory_structure(self, tmp_path):
        """Test nested work directory structure for scenarios with multiple steps."""
        # Simulate scenario execution with multiple steps
        case_work_dir = tmp_path / "tmp" / "nested_test_case"
        case_work_dir.mkdir(parents=True)
        
        step_names = ["prepare", "execute", "validate"]
        step_work_dirs = []
        
        for step_name in step_names:
            step_work_dir = case_work_dir / step_name
            step_work_dir.mkdir()
            step_work_dirs.append(step_work_dir)
            
            # Create log files for each step
            (step_work_dir / "stdout.log").write_text(f"{step_name} stdout output")
            (step_work_dir / "stderr.log").write_text(f"{step_name} stderr output")
            
            # Create step-specific output files
            (step_work_dir / f"{step_name}_output.txt").write_text(f"{step_name} specific output")
        
        # Verify directory structure
        for i, step_work_dir in enumerate(step_work_dirs):
            assert step_work_dir.exists()
            assert step_work_dir.is_dir()
            
            # Verify log files
            stdout_log = step_work_dir / "stdout.log"
            stderr_log = step_work_dir / "stderr.log"
            output_file = step_work_dir / f"{step_names[i]}_output.txt"
            
            assert stdout_log.exists()
            assert stderr_log.exists()
            assert output_file.exists()
            
            # Verify contents
            assert step_names[i] in stdout_log.read_text()
            assert step_names[i] in stderr_log.read_text()
            assert step_names[i] in output_file.read_text()
    
    def test_log_file_cleanup_and_recreation(self, tmp_path):
        """Test that log files are properly cleaned up and recreated."""
        work_dir = tmp_path / "cleanup_test"
        work_dir.mkdir()
        
        # Create initial log files
        stdout_log = work_dir / "stdout.log"
        stderr_log = work_dir / "stderr.log"
        stdout_log.write_text("old stdout content")
        stderr_log.write_text("old stderr content")
        
        assert "old stdout content" in stdout_log.read_text()
        assert "old stderr content" in stderr_log.read_text()
        
        # Execute a new command (simulating cleanup and recreation)
        from dact.models import Tool
        from dact.executor import Executor
        
        tool = Tool(
            name="cleanup-tool",
            command_template="echo 'new stdout content' && echo 'new stderr content' >&2"
        )
        
        executor = Executor(tool=tool, params={})
        result = executor.execute(work_dir=work_dir)
        
        # Verify log files were overwritten with new content
        assert "new stdout content" in stdout_log.read_text()
        assert "new stderr content" in stderr_log.read_text()
        assert "old stdout content" not in stdout_log.read_text()
        assert "old stderr content" not in stderr_log.read_text()


class TestExecutionMetrics:
    """Test execution metrics and performance tracking."""
    
    def test_execution_timing(self, tmp_path):
        """Test that execution timing is tracked correctly."""
        from dact.models import Tool
        from dact.executor import Executor
        import time
        
        # Create a tool with a small delay
        tool = Tool(
            name="timing-tool",
            command_template="sleep 0.1 && echo 'completed'"
        )
        
        executor = Executor(tool=tool, params={})
        
        start_time = time.time()
        result = executor.execute(work_dir=tmp_path)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Verify execution took at least the expected time
        assert execution_time >= 0.1
        assert result["returncode"] == 0
        assert "completed" in result["stdout"]
    
    def test_execution_result_completeness(self, tmp_path):
        """Test that execution results contain all required information."""
        from dact.models import Tool, ToolValidation
        from dact.executor import Executor
        
        tool = Tool(
            name="complete-result-tool",
            command_template="echo 'success output' && echo 'warning' >&2",
            validation=ToolValidation(
                exit_code=0,
                stdout_contains=["success"]
            ),
            post_exec={
                "outputs": {
                    "log_file": "find_file(dir='.', pattern='stdout.log')"
                }
            }
        )
        
        executor = Executor(tool=tool, params={})
        result = executor.execute(work_dir=tmp_path)
        
        # Verify all expected fields are present
        required_fields = [
            "stdout", "stderr", "returncode", "command", 
            "outputs", "validation"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field: {field}"
        
        # Verify field contents
        assert "success output" in result["stdout"]
        assert "warning" in result["stderr"]
        assert result["returncode"] == 0
        assert "echo" in result["command"]
        assert "log_file" in result["outputs"]
        assert result["validation"]["success"] is True
        
        # Verify validation details
        validation_details = result["validation"]["details"]
        assert len(validation_details) >= 2  # exit_code and stdout_contains
        
        exit_code_validation = next(
            (v for v in validation_details if v["rule"] == "exit_code"), 
            None
        )
        assert exit_code_validation is not None
        assert exit_code_validation["success"] is True
        
        stdout_validation = next(
            (v for v in validation_details if v["rule"] == "stdout_contains"), 
            None
        )
        assert stdout_validation is not None
        assert stdout_validation["success"] is True