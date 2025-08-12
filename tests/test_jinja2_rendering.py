import pytest
from pathlib import Path
from jinja2 import Environment
from dact.models import Step, Scenario
from dact.executor import Executor
from dact.tool_loader import load_tools_from_directory


class TestJinja2Rendering:
    """Test suite for Jinja2 template rendering functionality in scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.jinja_env = Environment()
    
    def test_basic_parameter_rendering(self):
        """Test basic parameter rendering with Jinja2 templates."""
        template_str = "Hello {{ name }}, you are {{ age }} years old"
        template = self.jinja_env.from_string(template_str)
        
        context = {"name": "Alice", "age": 30}
        result = template.render(**context)
        
        assert result == "Hello Alice, you are 30 years old"
    
    def test_step_output_reference_rendering(self):
        """Test rendering of step output references in parameters."""
        template_str = "Input file: {{ steps.generate_file.outputs.output_path }}"
        template = self.jinja_env.from_string(template_str)
        
        context = {
            "steps": {
                "generate_file": {
                    "outputs": {
                        "output_path": "/tmp/generated_file.txt"
                    }
                }
            }
        }
        
        result = template.render(**context)
        assert result == "Input file: /tmp/generated_file.txt"
    
    def test_nested_parameter_rendering(self):
        """Test rendering of nested parameters and complex expressions."""
        template_str = "{{ config.database.host }}:{{ config.database.port }}/{{ config.database.name }}"
        template = self.jinja_env.from_string(template_str)
        
        context = {
            "config": {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "name": "testdb"
                }
            }
        }
        
        result = template.render(**context)
        assert result == "localhost:5432/testdb"
    
    def test_conditional_rendering(self):
        """Test conditional rendering in templates."""
        template_str = "{% if debug %}--debug{% endif %} --output {{ output_dir }}"
        template = self.jinja_env.from_string(template_str)
        
        # Test with debug enabled
        context = {"debug": True, "output_dir": "/tmp/output"}
        result = template.render(**context)
        assert result == "--debug --output /tmp/output"
        
        # Test with debug disabled
        context = {"debug": False, "output_dir": "/tmp/output"}
        result = template.render(**context)
        assert result == " --output /tmp/output"
    
    def test_loop_rendering(self):
        """Test loop rendering in templates."""
        template_str = "{% for item in items %}--input {{ item }} {% endfor %}"
        template = self.jinja_env.from_string(template_str)
        
        context = {"items": ["file1.txt", "file2.txt", "file3.txt"]}
        result = template.render(**context)
        assert result == "--input file1.txt --input file2.txt --input file3.txt "
    
    def test_case_parameter_rendering(self):
        """Test rendering of case-level parameters."""
        template_str = "Processing case: {{ case.name }} with input: {{ case.input_file }}"
        template = self.jinja_env.from_string(template_str)
        
        context = {
            "case": {
                "name": "test_case_1",
                "input_file": "input.onnx"
            }
        }
        
        result = template.render(**context)
        assert result == "Processing case: test_case_1 with input: input.onnx"
    
    def test_default_parameter_rendering(self):
        """Test rendering with default parameters from scenario."""
        template_str = "Output directory: {{ output_dir | default('/tmp/default') }}"
        template = self.jinja_env.from_string(template_str)
        
        # Test with parameter provided
        context = {"output_dir": "/custom/output"}
        result = template.render(**context)
        assert result == "Output directory: /custom/output"
        
        # Test with default value
        context = {}
        result = template.render(**context)
        assert result == "Output directory: /tmp/default"
    
    def test_complex_step_chain_rendering(self):
        """Test rendering of complex step chains with multiple dependencies."""
        template_str = "{{ steps.step1.outputs.file }} -> {{ steps.step2.outputs.processed_file }}"
        template = self.jinja_env.from_string(template_str)
        
        context = {
            "steps": {
                "step1": {
                    "outputs": {
                        "file": "raw_data.txt"
                    }
                },
                "step2": {
                    "outputs": {
                        "processed_file": "processed_data.txt"
                    }
                }
            }
        }
        
        result = template.render(**context)
        assert result == "raw_data.txt -> processed_data.txt"
    
    def test_error_handling_missing_variable(self):
        """Test error handling when template variables are missing."""
        template_str = "Hello {{ missing_variable }}"
        template = self.jinja_env.from_string(template_str)
        
        context = {}
        
        # Jinja2 should raise an UndefinedError for missing variables
        from jinja2 import UndefinedError
        with pytest.raises(UndefinedError):
            template.render(**context)
    
    def test_parameter_override_rendering(self):
        """Test parameter override scenarios in step rendering."""
        # Simulate scenario default params being overridden by case params
        scenario_defaults = {"timeout": 30, "retries": 3}
        case_overrides = {"timeout": 60}  # Override timeout but keep retries
        
        # Merge parameters (case overrides scenario defaults)
        merged_params = {**scenario_defaults, **case_overrides}
        
        template_str = "Timeout: {{ timeout }}, Retries: {{ retries }}"
        template = self.jinja_env.from_string(template_str)
        
        result = template.render(**merged_params)
        assert result == "Timeout: 60, Retries: 3"


@pytest.fixture
def sample_tools_dir(tmp_path):
    """Create a temporary directory with sample tool definitions."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    
    # Create a simple tool for testing
    tool_content = """
name: test-tool
command_template: "echo '{{ message }}' > {{ output_file }}"
post_exec:
  outputs:
    output_file: "find_file(dir='{{ work_dir }}', pattern='*.txt')"
"""
    (tools_dir / "test-tool.tool.yml").write_text(tool_content)
    return tools_dir


class TestParameterPassingIntegration:
    """Integration tests for parameter passing in real scenario execution."""
    
    def test_step_parameter_rendering_with_context(self, sample_tools_dir, tmp_path):
        """Test parameter rendering in the context of step execution."""
        # Load tools
        tools = load_tools_from_directory(str(sample_tools_dir))
        
        # Create a run context simulating previous step outputs
        run_context = {
            "steps": {
                "previous_step": {
                    "outputs": {
                        "generated_file": "test_output.txt"
                    }
                }
            },
            "case": {
                "name": "integration_test"
            }
        }
        
        # Create step with template parameters
        step_params = {
            "message": "Hello from {{ case.name }}",
            "output_file": "result_{{ steps.previous_step.outputs.generated_file }}"
        }
        
        # Render parameters using Jinja2
        jinja_env = Environment()
        rendered_params = {}
        for key, value in step_params.items():
            if isinstance(value, str):
                template = jinja_env.from_string(value)
                rendered_params[key] = template.render(**run_context)
            else:
                rendered_params[key] = value
        
        # Verify rendered parameters
        assert rendered_params["message"] == "Hello from integration_test"
        assert rendered_params["output_file"] == "result_test_output.txt"
        
        # Test with executor (mock execution)
        tool = tools["test-tool"]
        executor = Executor(tool=tool, params=rendered_params)
        
        # Verify command template rendering
        template = jinja_env.from_string(tool.command_template)
        rendered_command = template.render(**rendered_params)
        expected_command = "echo 'Hello from integration_test' > result_test_output.txt"
        assert rendered_command == expected_command
    
    def test_scenario_dependency_integration(self):
        """Test integration of dependency resolution with parameter passing."""
        from dact.dependency_resolver import DependencyResolver
        
        scenario = Scenario(
            name="integration_scenario",
            default_params={
                "base_dir": "/tmp/test",
                "format": "json"
            },
            steps=[
                Step(name="init", tool="init_tool"),
                Step(
                    name="process",
                    tool="process_tool",
                    params={
                        "config": "{{ steps.init.outputs.config_file }}",
                        "output_dir": "{{ base_dir }}/processed"
                    }
                ),
                Step(
                    name="finalize",
                    tool="final_tool",
                    params={
                        "input": "{{ steps.process.outputs.result }}",
                        "format": "{{ format }}"
                    }
                )
            ]
        )
        
        resolver = DependencyResolver()
        dependency_graph = resolver.extract_dependencies(scenario)
        
        # Verify execution order
        expected_order = [["init"], ["process"], ["finalize"]]
        assert dependency_graph.execution_order == expected_order
        
        # Verify dependencies are correctly extracted from templates
        assert "init" in dependency_graph.nodes["process"].dependencies
        assert "process" in dependency_graph.nodes["finalize"].dependencies
        
        # Test parameter rendering with scenario defaults
        jinja_env = Environment()
        context = {**scenario.default_params, "steps": {"init": {"outputs": {"config_file": "/tmp/config.json"}}}}
        
        process_params = scenario.steps[1].params.copy()
        rendered_params = {}
        for key, value in process_params.items():
            template = jinja_env.from_string(value)
            rendered_params[key] = template.render(**context)
        
        assert rendered_params["config"] == "/tmp/config.json"
        assert rendered_params["output_dir"] == "/tmp/test/processed"