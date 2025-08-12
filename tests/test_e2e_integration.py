#!/usr/bin/env python3
"""
End-to-End Integration Tests for DACT Pipeline

This module contains integration tests that validate the complete
end-to-end functionality of the DACT pipeline system.
"""

import os
import sys
import tempfile
import shutil
import pytest
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dact.tool_loader import load_tools_from_directory
from dact.scenario_loader import load_scenarios_from_directory
from dact.executor import Executor, POST_EXEC_FUNCTIONS
from dact.models import Tool, Scenario


class TestE2EIntegration:
    """End-to-End Integration Test Suite"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="dact_e2e_test_"))
        self.original_cwd = os.getcwd()
        os.chdir(project_root)
    
    def teardown_method(self):
        """Cleanup test environment"""
        os.chdir(self.original_cwd)
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_tool_loading(self):
        """Test that all required tools can be loaded"""
        tools = load_tools_from_directory("tools")
        
        # Verify required tools exist
        required_tools = ["ai-json-operator", "atc", "file-validator", "demo-tool"]
        for tool_name in required_tools:
            assert tool_name in tools, f"Required tool '{tool_name}' not found"
        
        # Verify tool configurations are valid
        for tool_name, tool in tools.items():
            assert isinstance(tool, Tool), f"Tool '{tool_name}' is not a valid Tool instance"
            assert tool.name == tool_name, f"Tool name mismatch: {tool.name} != {tool_name}"
            assert tool.command_template, f"Tool '{tool_name}' missing command template"
    
    def test_scenario_loading(self):
        """Test that scenarios can be loaded and validated"""
        scenarios = load_scenarios_from_directory("scenarios")
        
        # Verify e2e scenario exists
        assert "e2e-onnx-to-atc" in scenarios, "E2E scenario not found"
        
        e2e_scenario = scenarios["e2e-onnx-to-atc"]
        assert isinstance(e2e_scenario, Scenario), "E2E scenario is not a valid Scenario instance"
        
        # Verify scenario structure
        assert len(e2e_scenario.steps) >= 3, "E2E scenario should have at least 3 steps"
        
        step_names = [step.name for step in e2e_scenario.steps]
        expected_steps = ["generate_onnx", "convert_atc", "validate_output"]
        for expected_step in expected_steps:
            assert expected_step in step_names, f"Expected step '{expected_step}' not found"
    
    def test_post_exec_functions(self):
        """Test that all required post_exec functions are available"""
        required_functions = [
            "find_file",
            "find_latest_file", 
            "find_onnx_file",
            "find_onnx_dir",
            "check_file_exists"
        ]
        
        for func_name in required_functions:
            assert func_name in POST_EXEC_FUNCTIONS, f"Required function '{func_name}' not found"
            assert callable(POST_EXEC_FUNCTIONS[func_name]), f"Function '{func_name}' is not callable"
    
    def test_find_onnx_file_function(self):
        """Test the find_onnx_file function with mock data"""
        # Create mock directory structure
        mock_dir = self.test_dir / "mock_output"
        mock_subdir = mock_dir / "Conv_testcase_98bd3f" / "resources"
        mock_subdir.mkdir(parents=True)
        
        # Create mock ONNX file
        mock_onnx_file = mock_subdir / "Conv_testcase_98bd3f.onnx"
        mock_onnx_file.write_text("mock onnx content")
        
        # Test find_onnx_file function
        find_onnx_file = POST_EXEC_FUNCTIONS["find_onnx_file"]
        found_file = find_onnx_file(str(mock_dir))
        
        assert found_file == str(mock_onnx_file), f"Expected {mock_onnx_file}, got {found_file}"
    
    def test_find_onnx_dir_function(self):
        """Test the find_onnx_dir function with mock data"""
        # Create mock directory structure
        mock_dir = self.test_dir / "mock_output"
        mock_subdir = mock_dir / "Conv_testcase_98bd3f" / "resources"
        mock_subdir.mkdir(parents=True)
        
        # Create mock ONNX file
        mock_onnx_file = mock_subdir / "Conv_testcase_98bd3f.onnx"
        mock_onnx_file.write_text("mock onnx content")
        
        # Test find_onnx_dir function
        find_onnx_dir = POST_EXEC_FUNCTIONS["find_onnx_dir"]
        found_dir = find_onnx_dir(str(mock_dir))
        
        assert found_dir == str(mock_subdir), f"Expected {mock_subdir}, got {found_dir}"
    
    def test_file_validator_tool_execution(self):
        """Test file validator tool execution"""
        tools = load_tools_from_directory("tools")
        file_validator = tools["file-validator"]
        
        # Create test files
        test_dir = self.test_dir / "validator_test"
        test_dir.mkdir()
        (test_dir / "test1.txt").write_text("test content 1")
        (test_dir / "test2.txt").write_text("test content 2")
        
        # Execute file validator
        executor = Executor(file_validator, {
            "check_path": str(test_dir),
            "expected_files": ["*.txt"],
            "min_size": 5,
            "recursive": False
        })
        
        result = executor.execute(self.test_dir)
        
        # Verify execution results
        assert result["returncode"] == 0, f"File validator failed: {result['stderr']}"
        assert "validation" in result, "Validation results missing"
        assert result["validation"]["success"], f"Validation failed: {result['validation']}"
    
    def test_tool_parameter_rendering(self):
        """Test Jinja2 parameter rendering in tools"""
        tools = load_tools_from_directory("tools")
        ai_json_operator = tools["ai-json-operator"]
        
        # Test parameter rendering
        executor = Executor(ai_json_operator, {
            "ops": "Conv Add",
            "convert_to_onnx": True,
            "max_retries": 3,
            "output_dir": "test_output"
        })
        
        # Render command template
        from jinja2 import Environment
        jinja_env = Environment()
        template = jinja_env.from_string(ai_json_operator.command_template)
        rendered_command = template.render(**executor.params)
        
        # Verify rendered command
        assert "Conv Add" in rendered_command, "ops parameter not rendered"
        assert "--convert-to-onnx" in rendered_command, "convert_to_onnx flag not rendered"
        assert "--max-retries 3" in rendered_command, "max_retries parameter not rendered"
        assert "-o test_output" in rendered_command, "output_dir parameter not rendered"
    
    def test_scenario_step_dependencies(self):
        """Test scenario step dependency resolution"""
        scenarios = load_scenarios_from_directory("scenarios")
        e2e_scenario = scenarios["e2e-onnx-to-atc"]
        
        # Find steps with dependencies
        dependent_steps = [step for step in e2e_scenario.steps if hasattr(step, 'depends_on') and step.depends_on]
        
        assert len(dependent_steps) > 0, "No dependent steps found in e2e scenario"
        
        # Verify dependency references are valid
        step_names = [step.name for step in e2e_scenario.steps]
        for step in dependent_steps:
            for dependency in step.depends_on:
                assert dependency in step_names, f"Invalid dependency '{dependency}' in step '{step.name}'"
    
    def test_validation_rules(self):
        """Test tool validation rules"""
        tools = load_tools_from_directory("tools")
        
        # Test tools with validation rules
        tools_with_validation = [tool for tool in tools.values() if tool.validation]
        assert len(tools_with_validation) > 0, "No tools with validation rules found"
        
        for tool in tools_with_validation:
            validation = tool.validation
            
            # Verify validation structure
            if validation.exit_code is not None:
                assert isinstance(validation.exit_code, int), f"Invalid exit_code in {tool.name}"
            
            if validation.stdout_contains:
                assert isinstance(validation.stdout_contains, list), f"Invalid stdout_contains in {tool.name}"
            
            if validation.stderr_not_contains:
                assert isinstance(validation.stderr_not_contains, list), f"Invalid stderr_not_contains in {tool.name}"
            
            if validation.output_files_exist:
                assert isinstance(validation.output_files_exist, list), f"Invalid output_files_exist in {tool.name}"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])