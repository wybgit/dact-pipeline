"""
Tests for the enhanced test case system including validation and data-driven testing.
"""
import pytest
import tempfile
import yaml
import json
import csv
from pathlib import Path
from unittest.mock import Mock, patch
from dact.models import Case, CaseFile, CaseValidation, DataDrivenCase
from dact.validation_engine import ValidationEngine, ValidationResult
from dact.data_providers import CSVDataProvider, JSONDataProvider, YAMLDataProvider, load_test_data


class TestCaseValidation:
    """Test the CaseValidation model and validation types."""
    
    def test_case_validation_model(self):
        """Test CaseValidation model creation and validation."""
        # Test basic validation
        validation = CaseValidation(
            type="exit_code",
            expected=0,
            description="Check successful execution"
        )
        assert validation.type == "exit_code"
        assert validation.expected == 0
        assert validation.description == "Check successful execution"
        
        # Test file validation
        file_validation = CaseValidation(
            type="file_exists",
            target="output.txt",
            description="Check output file exists"
        )
        assert file_validation.type == "file_exists"
        assert file_validation.target == "output.txt"
        
        # Test pattern validation
        pattern_validation = CaseValidation(
            type="output_matches",
            target="result",
            pattern=r"\d+\.\d+",
            description="Check numeric output format"
        )
        assert pattern_validation.pattern == r"\d+\.\d+"


class TestValidationEngine:
    """Test the ValidationEngine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ValidationEngine()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_exit_code_validation_success(self):
        """Test successful exit code validation."""
        validation = CaseValidation(type="exit_code", expected=0)
        execution_result = {"returncode": 0}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
        assert "Expected exit code 0, got 0" in result.message
    
    def test_exit_code_validation_failure(self):
        """Test failed exit code validation."""
        validation = CaseValidation(type="exit_code", expected=0)
        execution_result = {"returncode": 1}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert not result.is_valid
        assert "Expected exit code 0, got 1" in result.message
    
    def test_stdout_contains_validation_success(self):
        """Test successful stdout contains validation."""
        validation = CaseValidation(type="stdout_contains", expected="success")
        execution_result = {"stdout": "Operation completed successfully"}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
    
    def test_stdout_contains_validation_failure(self):
        """Test failed stdout contains validation."""
        validation = CaseValidation(type="stdout_contains", expected="success")
        execution_result = {"stdout": "Operation failed"}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert not result.is_valid
        assert "Expected stdout to contain 'success'" in result.message
    
    def test_file_exists_validation_success(self):
        """Test successful file exists validation."""
        # Create a test file
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("test content")
        
        validation = CaseValidation(type="file_exists", target="test.txt")
        execution_result = {}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
    
    def test_file_exists_validation_failure(self):
        """Test failed file exists validation."""
        validation = CaseValidation(type="file_exists", target="nonexistent.txt")
        execution_result = {}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert not result.is_valid
        assert "Expected file 'nonexistent.txt' to exist" in result.message
    
    def test_file_size_validation(self):
        """Test file size validation."""
        # Create a test file with known size
        test_file = self.temp_dir / "test.txt"
        content = "Hello, World!"
        test_file.write_text(content)
        expected_size = len(content.encode('utf-8'))
        
        validation = CaseValidation(
            type="file_size", 
            target="test.txt", 
            expected=expected_size,
            tolerance=0
        )
        execution_result = {}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
    
    def test_output_equals_validation(self):
        """Test output equals validation."""
        validation = CaseValidation(type="output_equals", target="result", expected="42")
        execution_result = {"outputs": {"result": "42"}}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
    
    def test_output_matches_validation(self):
        """Test output matches regex validation."""
        validation = CaseValidation(
            type="output_matches", 
            target="version", 
            pattern=r"v\d+\.\d+\.\d+"
        )
        execution_result = {"outputs": {"version": "v1.2.3"}}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
    
    def test_custom_validation(self):
        """Test custom validation function."""
        def custom_validator(validation, execution_result, work_dir):
            return ValidationResult(True, "Custom validation passed")
        
        self.engine.register_custom_validator("test_validator", custom_validator)
        
        validation = CaseValidation(type="custom", custom_validator="test_validator")
        execution_result = {}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
        assert "Custom validation passed" in result.message
    
    def test_unknown_validation_type(self):
        """Test handling of unknown validation type."""
        validation = CaseValidation(type="unknown_type")
        execution_result = {}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert not result.is_valid
        assert "Unknown validation type: unknown_type" in result.message


class TestDataProviders:
    """Test data providers for data-driven testing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_csv_data_provider(self):
        """Test CSV data provider."""
        # Create test CSV file
        csv_file = self.temp_dir / "test_data.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'value', 'expected'])
            writer.writerow(['test1', '10', 'true'])
            writer.writerow(['test2', '20', 'false'])
        
        provider = CSVDataProvider()
        data = provider.load_data(str(csv_file))
        
        assert len(data) == 2
        assert data[0]['name'] == 'test1'
        assert data[0]['value'] == 10  # Should be converted to int
        assert data[1]['expected'] == False  # Should be converted to bool
    
    def test_json_data_provider(self):
        """Test JSON data provider."""
        # Create test JSON file
        json_file = self.temp_dir / "test_data.json"
        test_data = [
            {"name": "test1", "value": 10, "expected": True},
            {"name": "test2", "value": 20, "expected": False}
        ]
        with open(json_file, 'w') as f:
            json.dump(test_data, f)
        
        provider = JSONDataProvider()
        data = provider.load_data(str(json_file))
        
        assert len(data) == 2
        assert data[0]['name'] == 'test1'
        assert data[0]['value'] == 10
        assert data[1]['expected'] == False
    
    def test_yaml_data_provider(self):
        """Test YAML data provider."""
        # Create test YAML file
        yaml_file = self.temp_dir / "test_data.yaml"
        test_data = [
            {"name": "test1", "value": 10, "expected": True},
            {"name": "test2", "value": 20, "expected": False}
        ]
        with open(yaml_file, 'w') as f:
            yaml.dump(test_data, f)
        
        provider = YAMLDataProvider()
        data = provider.load_data(str(yaml_file))
        
        assert len(data) == 2
        assert data[0]['name'] == 'test1'
        assert data[0]['value'] == 10
    
    def test_load_test_data_convenience_function(self):
        """Test the convenience function for loading test data."""
        # Create test JSON file
        json_file = self.temp_dir / "test_data.json"
        test_data = [{"name": "test1", "value": 10}]
        with open(json_file, 'w') as f:
            json.dump(test_data, f)
        
        data = load_test_data(str(json_file))
        
        assert len(data) == 1
        assert data[0]['name'] == 'test1'
    
    def test_data_validation_schema(self):
        """Test data validation against schema."""
        provider = JSONDataProvider()
        data = [
            {"name": "test1", "value": 10},
            {"name": "test2", "value": 20}
        ]
        
        # Valid schema
        schema = {"required_fields": ["name", "value"]}
        assert provider.validate_data_schema(data, schema)
        
        # Invalid schema - missing required field
        schema = {"required_fields": ["name", "value", "missing"]}
        assert not provider.validate_data_schema(data, schema)


class TestEnhancedCaseModel:
    """Test the enhanced Case model with new features."""
    
    def test_enhanced_case_model(self):
        """Test the enhanced Case model with all new fields."""
        case = Case(
            name="enhanced_test",
            description="Test with all features",
            tags=["integration", "slow"],
            scenario="test_scenario",
            params={"param1": "value1"},
            validation=[
                CaseValidation(type="exit_code", expected=0),
                CaseValidation(type="file_exists", target="output.txt")
            ],
            setup={"create_dirs": ["temp", "output"]},
            teardown={"cleanup": True},
            timeout=300,
            retry_count=2
        )
        
        assert case.name == "enhanced_test"
        assert "integration" in case.tags
        assert len(case.validation) == 2
        assert case.timeout == 300
        assert case.retry_count == 2
    
    def test_data_driven_case_model(self):
        """Test the DataDrivenCase model."""
        template_case = Case(
            name="template_test",
            scenario="test_scenario",
            params={"param1": "{{ data.value }}"}
        )
        
        data_driven_case = DataDrivenCase(
            template=template_case,
            data_source="test_data.csv",
            parameter_mapping={"param1": "value_column"}
        )
        
        assert data_driven_case.template.name == "template_test"
        assert data_driven_case.data_source == "test_data.csv"
        assert data_driven_case.parameter_mapping["param1"] == "value_column"
    
    def test_case_file_with_data_driven_cases(self):
        """Test CaseFile with data-driven cases."""
        template_case = Case(name="template", scenario="test")
        data_driven_case = DataDrivenCase(
            template=template_case,
            data_source="data.csv"
        )
        
        case_file = CaseFile(
            common_params={"timeout": 60},
            cases=[Case(name="regular_test", tool="test_tool")],
            data_driven_cases=[data_driven_case]
        )
        
        assert len(case_file.cases) == 1
        assert len(case_file.data_driven_cases) == 1
        assert case_file.common_params["timeout"] == 60


class TestParameterOverride:
    """Test parameter override mechanisms."""
    
    def test_common_params_override(self):
        """Test that common_params are applied to all cases."""
        case_file = CaseFile(
            common_params={"timeout": 60, "retries": 3},
            cases=[
                Case(name="test1", tool="tool1", params={"param1": "value1"}),
                Case(name="test2", tool="tool2", params={"timeout": 120})  # Override timeout
            ]
        )
        
        # Simulate the parameter merging logic from pytest_plugin
        for case in case_file.cases:
            merged_params = case_file.common_params.copy()
            merged_params.update(case.params)
            case.params = merged_params
        
        # test1 should have all common params plus its own
        assert case_file.cases[0].params["timeout"] == 60
        assert case_file.cases[0].params["retries"] == 3
        assert case_file.cases[0].params["param1"] == "value1"
        
        # test2 should override timeout but keep retries
        assert case_file.cases[1].params["timeout"] == 120  # Overridden
        assert case_file.cases[1].params["retries"] == 3    # From common_params
    
    def test_scenario_step_parameter_override(self):
        """Test that case params can override scenario step parameters."""
        # This would be tested in integration with the pytest plugin
        # Here we just verify the model structure supports it
        case = Case(
            name="test_override",
            scenario="multi_step_scenario",
            params={
                "step1": {"param1": "overridden_value"},
                "step2": {"param2": "another_override"}
            }
        )
        
        assert case.params["step1"]["param1"] == "overridden_value"
        assert case.params["step2"]["param2"] == "another_override"


class TestDataDrivenIntegration:
    """Test data-driven testing integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_parameter_mapping_simple(self):
        """Test simple parameter mapping from data to case parameters."""
        # This simulates the _apply_parameter_mapping method
        data_row = {"test_name": "conv_test", "input_size": 224, "batch_size": 1}
        parameter_mapping = {
            "name": "test_name",
            "input_size": "input_size",
            "batch_size": "batch_size"
        }
        
        # Simulate the mapping logic
        mapped_params = {}
        for param_path, data_key in parameter_mapping.items():
            if data_key in data_row:
                mapped_params[param_path] = data_row[data_key]
        
        assert mapped_params["name"] == "conv_test"
        assert mapped_params["input_size"] == 224
        assert mapped_params["batch_size"] == 1
    
    def test_parameter_mapping_nested(self):
        """Test nested parameter mapping for step-specific parameters."""
        data_row = {"model_name": "resnet", "soc_version": "Ascend310"}
        parameter_mapping = {
            "generate_onnx.model": "model_name",
            "convert_atc.soc_version": "soc_version"
        }
        
        # Simulate nested parameter mapping
        mapped_params = {}
        for param_path, data_key in parameter_mapping.items():
            if data_key in data_row:
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
        
        assert mapped_params["generate_onnx"]["model"] == "resnet"
        assert mapped_params["convert_atc"]["soc_version"] == "Ascend310"


if __name__ == "__main__":
    pytest.main([__file__])