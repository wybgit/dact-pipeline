"""
Unit tests for step parameter passing functionality.
"""
import pytest
from pathlib import Path
from jinja2 import Environment
from dact.models import Scenario, Step, CaseFile, Case
from dact.dependency_resolver import DependencyResolver
from dact.pytest_plugin import TestCaseItem


class TestStepParameterPassing:
    """Test suite for step parameter passing functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.jinja_env = Environment()
        self.resolver = DependencyResolver()
    
    def test_basic_parameter_passing(self):
        """Test basic parameter passing between steps."""
        run_context = {
            "steps": {
                "step1": {
                    "outputs": {
                        "file_path": "/tmp/output.txt",
                        "status": "success"
                    }
                }
            }
        }
        
        params = {
            "input_file": "{{ steps.step1.outputs.file_path }}",
            "check_status": "{{ steps.step1.outputs.status }}"
        }
        
        rendered_params = {}
        for key, value in params.items():
            if isinstance(value, str):
                template = self.jinja_env.from_string(value)
                rendered_params[key] = template.render(**run_context)
            else:
                rendered_params[key] = value
        
        assert rendered_params["input_file"] == "/tmp/output.txt"
        assert rendered_params["check_status"] == "success"
    
    def test_nested_parameter_passing(self):
        """Test nested parameter passing with complex data structures."""
        run_context = {
            "steps": {
                "config_step": {
                    "outputs": {
                        "config": {
                            "database": {
                                "host": "localhost",
                                "port": 5432
                            },
                            "api": {
                                "endpoint": "https://api.example.com"
                            }
                        }
                    }
                }
            }
        }
        
        params = {
            "db_host": "{{ steps.config_step.outputs.config.database.host }}",
            "db_port": "{{ steps.config_step.outputs.config.database.port }}",
            "api_url": "{{ steps.config_step.outputs.config.api.endpoint }}"
        }
        
        rendered_params = {}
        for key, value in params.items():
            template = self.jinja_env.from_string(value)
            rendered_params[key] = template.render(**run_context)
        
        assert rendered_params["db_host"] == "localhost"
        assert rendered_params["db_port"] == "5432"  # Jinja2 converts to string
        assert rendered_params["api_url"] == "https://api.example.com"
    
    def test_parameter_override_hierarchy(self):
        """Test parameter override hierarchy: case > step > scenario defaults."""
        scenario_defaults = {
            "timeout": 30,
            "retries": 3,
            "output_dir": "/tmp/default"
        }
        
        step_params = {
            "timeout": 60,  # Override scenario default
            "input_file": "test.txt"
        }
        
        case_overrides = {
            "retries": 5,  # Override scenario default
            "debug": True  # New parameter
        }
        
        # Simulate parameter merging logic
        final_params = {}
        final_params.update(scenario_defaults)  # Start with scenario defaults
        final_params.update(step_params)        # Apply step-specific params
        final_params.update(case_overrides)     # Apply case overrides
        
        assert final_params["timeout"] == 60      # From step
        assert final_params["retries"] == 5       # From case
        assert final_params["output_dir"] == "/tmp/default"  # From scenario
        assert final_params["input_file"] == "test.txt"      # From step
        assert final_params["debug"] is True      # From case
    
    def test_conditional_parameter_rendering(self):
        """Test conditional parameter rendering."""
        run_context = {
            "debug_mode": True,
            "environment": "development",
            "steps": {
                "setup": {
                    "outputs": {
                        "config_file": "/tmp/dev_config.json"
                    }
                }
            }
        }
        
        params = {
            "log_level": "{% if debug_mode %}debug{% else %}info{% endif %}",
            "config": "{% if environment == 'development' %}{{ steps.setup.outputs.config_file }}{% else %}/etc/prod_config.json{% endif %}"
        }
        
        rendered_params = {}
        for key, value in params.items():
            template = self.jinja_env.from_string(value)
            rendered_params[key] = template.render(**run_context)
        
        assert rendered_params["log_level"] == "debug"
        assert rendered_params["config"] == "/tmp/dev_config.json"
    
    def test_list_parameter_rendering(self):
        """Test rendering of list parameters."""
        run_context = {
            "steps": {
                "gather_files": {
                    "outputs": {
                        "files": ["file1.txt", "file2.txt", "file3.txt"]
                    }
                }
            }
        }
        
        params = {
            "input_files": "{{ steps.gather_files.outputs.files | join(',') }}",
            "file_count": "{{ steps.gather_files.outputs.files | length }}"
        }
        
        rendered_params = {}
        for key, value in params.items():
            template = self.jinja_env.from_string(value)
            rendered_params[key] = template.render(**run_context)
        
        assert rendered_params["input_files"] == "file1.txt,file2.txt,file3.txt"
        assert rendered_params["file_count"] == "3"
    
    def test_error_handling_missing_step_output(self):
        """Test error handling when referencing missing step outputs."""
        run_context = {
            "steps": {
                "step1": {
                    "outputs": {
                        "existing_output": "value"
                    }
                }
            }
        }
        
        params = {
            "valid_param": "{{ steps.step1.outputs.existing_output }}",
            "invalid_param": "{{ steps.step1.outputs.missing_output }}"
        }
        
        # Valid parameter should render correctly
        template = self.jinja_env.from_string(params["valid_param"])
        result = template.render(**run_context)
        assert result == "value"
        
        # Invalid parameter should raise an error
        from jinja2 import UndefinedError
        template = self.jinja_env.from_string(params["invalid_param"])
        with pytest.raises(UndefinedError):
            template.render(**run_context)
    
    def test_case_level_parameter_injection(self):
        """Test injection of case-level parameters into step context."""
        case_context = {
            "case": {
                "name": "test_case_1",
                "input_file": "input.onnx",
                "output_dir": "/tmp/test_output"
            }
        }
        
        params = {
            "case_name": "{{ case.name }}",
            "input": "{{ case.input_file }}",
            "output": "{{ case.output_dir }}/{{ case.name }}_result.txt"
        }
        
        rendered_params = {}
        for key, value in params.items():
            template = self.jinja_env.from_string(value)
            rendered_params[key] = template.render(**case_context)
        
        assert rendered_params["case_name"] == "test_case_1"
        assert rendered_params["input"] == "input.onnx"
        assert rendered_params["output"] == "/tmp/test_output/test_case_1_result.txt"
    
    def test_recursive_parameter_rendering(self):
        """Test recursive parameter rendering for nested data structures."""
        # This simulates the _render_parameters method from pytest_plugin
        def render_parameters(params, context, jinja_env):
            rendered_params = {}
            
            for key, value in params.items():
                if isinstance(value, str):
                    template = jinja_env.from_string(value)
                    rendered_params[key] = template.render(**context)
                elif isinstance(value, dict):
                    rendered_params[key] = render_parameters(value, context, jinja_env)
                elif isinstance(value, list):
                    rendered_params[key] = [
                        render_parameters(item, context, jinja_env) if isinstance(item, dict)
                        else jinja_env.from_string(str(item)).render(**context) if isinstance(item, str)
                        else item
                        for item in value
                    ]
                else:
                    rendered_params[key] = value
            
            return rendered_params
        
        context = {
            "base_path": "/tmp",
            "case_name": "test_case"
        }
        
        params = {
            "simple_param": "{{ base_path }}/{{ case_name }}",
            "nested_dict": {
                "input_dir": "{{ base_path }}/input",
                "output_dir": "{{ base_path }}/output/{{ case_name }}"
            },
            "param_list": [
                "{{ base_path }}/file1.txt",
                "{{ base_path }}/file2.txt",
                {"path": "{{ base_path }}/nested/{{ case_name }}.log"}
            ]
        }
        
        rendered = render_parameters(params, context, self.jinja_env)
        
        assert rendered["simple_param"] == "/tmp/test_case"
        assert rendered["nested_dict"]["input_dir"] == "/tmp/input"
        assert rendered["nested_dict"]["output_dir"] == "/tmp/output/test_case"
        assert rendered["param_list"][0] == "/tmp/file1.txt"
        assert rendered["param_list"][1] == "/tmp/file2.txt"
        assert rendered["param_list"][2]["path"] == "/tmp/nested/test_case.log"
    
    def test_scenario_default_params_integration(self):
        """Test integration of scenario default parameters."""
        scenario = Scenario(
            name="test_scenario",
            default_params={
                "timeout": 30,
                "output_format": "json",
                "base_dir": "/tmp/scenario"
            },
            steps=[
                Step(
                    name="step1",
                    tool="tool1",
                    params={
                        "timeout": "{{ timeout }}",
                        "output": "{{ base_dir }}/step1_output.{{ output_format }}"
                    }
                ),
                Step(
                    name="step2",
                    tool="tool2",
                    params={
                        "input": "{{ steps.step1.outputs.result }}",
                        "timeout": 60,  # Override scenario default
                        "format": "{{ output_format }}"
                    }
                )
            ]
        )
        
        # Simulate parameter merging for step1
        step1_params = scenario.steps[0].params.copy()
        for key, value in scenario.default_params.items():
            if key not in step1_params:
                step1_params[key] = value
        
        context = {**scenario.default_params}
        rendered_step1 = {}
        for key, value in step1_params.items():
            if isinstance(value, str):
                template = self.jinja_env.from_string(value)
                rendered_step1[key] = template.render(**context)
            else:
                rendered_step1[key] = value
        
        assert rendered_step1["timeout"] == "30"
        assert rendered_step1["output"] == "/tmp/scenario/step1_output.json"
        
        # Simulate parameter merging for step2 (with override)
        step2_params = scenario.steps[1].params.copy()
        for key, value in scenario.default_params.items():
            if key not in step2_params:
                step2_params[key] = value
        
        # step2 has timeout=60 which should override the scenario default
        assert step2_params["timeout"] == 60
        assert step2_params["format"] == "json"  # From scenario defaults


class TestParameterPassingEdgeCases:
    """Test edge cases in parameter passing."""
    
    def setup_method(self):
        """Set up test environment."""
        self.jinja_env = Environment()
    
    def test_empty_step_outputs(self):
        """Test handling of empty step outputs."""
        run_context = {
            "steps": {
                "empty_step": {
                    "outputs": {}
                }
            }
        }
        
        params = {
            "default_value": "{{ steps.empty_step.outputs.missing | default('fallback') }}"
        }
        
        template = self.jinja_env.from_string(params["default_value"])
        result = template.render(**run_context)
        assert result == "fallback"
    
    def test_step_with_no_outputs(self):
        """Test handling of steps with no outputs section."""
        run_context = {
            "steps": {
                "no_outputs_step": {}
            }
        }
        
        params = {
            "safe_access": "{{ steps.no_outputs_step.outputs.value | default('no_output') }}"
        }
        
        template = self.jinja_env.from_string(params["safe_access"])
        result = template.render(**run_context)
        assert result == "no_output"
    
    def test_numeric_parameter_rendering(self):
        """Test rendering of numeric parameters."""
        run_context = {
            "steps": {
                "counter": {
                    "outputs": {
                        "count": 42,
                        "percentage": 85.5
                    }
                }
            }
        }
        
        params = {
            "count_str": "{{ steps.counter.outputs.count }}",
            "percentage_str": "{{ steps.counter.outputs.percentage }}",
            "calculated": "{{ steps.counter.outputs.count * 2 }}"
        }
        
        rendered_params = {}
        for key, value in params.items():
            template = self.jinja_env.from_string(value)
            rendered_params[key] = template.render(**run_context)
        
        assert rendered_params["count_str"] == "42"
        assert rendered_params["percentage_str"] == "85.5"
        assert rendered_params["calculated"] == "84"
    
    def test_boolean_parameter_rendering(self):
        """Test rendering of boolean parameters."""
        run_context = {
            "debug": True,
            "production": False
        }
        
        params = {
            "debug_flag": "{% if debug %}--debug{% endif %}",
            "env_flag": "{% if not production %}--dev-mode{% endif %}"
        }
        
        rendered_params = {}
        for key, value in params.items():
            template = self.jinja_env.from_string(value)
            rendered_params[key] = template.render(**run_context)
        
        assert rendered_params["debug_flag"] == "--debug"
        assert rendered_params["env_flag"] == "--dev-mode"