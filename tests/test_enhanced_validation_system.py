"""
Tests for the enhanced validation system with new validation types.
"""
import pytest
import tempfile
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
from dact.models import CaseValidation
from dact.validation_engine import ValidationEngine, ValidationResult


class TestEnhancedValidationTypes:
    """Test the new validation types in the enhanced system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ValidationEngine()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_file_content_validation_exact_match(self):
        """Test file content validation with exact match."""
        # Create test file
        test_file = self.temp_dir / "content.txt"
        expected_content = "Hello, World!\nThis is a test file."
        test_file.write_text(expected_content)
        
        validation = CaseValidation(
            type="file_content",
            target="content.txt",
            expected=expected_content
        )
        execution_result = {}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
        assert "Expected file content to match exactly" in result.message
    
    def test_file_content_validation_pattern_match(self):
        """Test file content validation with pattern matching."""
        # Create test file
        test_file = self.temp_dir / "log.txt"
        test_file.write_text("2023-01-01 10:30:45 INFO: Process completed successfully")
        
        validation = CaseValidation(
            type="file_content",
            target="log.txt",
            pattern=r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} INFO:"
        )
        execution_result = {}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
    
    def test_file_content_validation_encoding(self):
        """Test file content validation with different encoding."""
        # Create test file with UTF-8 content
        test_file = self.temp_dir / "unicode.txt"
        content = "测试内容 - Test Content"
        test_file.write_text(content, encoding="utf-8")
        
        validation = CaseValidation(
            type="file_content",
            target="unicode.txt",
            expected=content,
            encoding="utf-8"
        )
        execution_result = {}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
    
    def test_performance_validation_with_tolerance(self):
        """Test performance validation with tolerance."""
        validation = CaseValidation(
            type="performance",
            target="execution_time",
            expected=5.0,
            tolerance=0.5
        )
        execution_result = {
            "metrics": {
                "execution_time": 5.3  # Within tolerance
            }
        }
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
        assert "5.0 ± 0.5" in result.message
    
    def test_performance_validation_range(self):
        """Test performance validation with min/max range."""
        validation = CaseValidation(
            type="performance",
            target="memory_usage",
            min_value=100.0,
            max_value=500.0
        )
        execution_result = {
            "metrics": {
                "memory_usage": 250.0  # Within range
            }
        }
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
        assert "within acceptable range" in result.message
    
    def test_performance_validation_out_of_range(self):
        """Test performance validation failure when out of range."""
        validation = CaseValidation(
            type="performance",
            target="cpu_usage",
            min_value=10.0,
            max_value=80.0
        )
        execution_result = {
            "metrics": {
                "cpu_usage": 95.0  # Above maximum
            }
        }
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert not result.is_valid
        assert "above maximum 80.0" in result.message
    
    @patch('dact.validation_engine.jsonschema')
    def test_json_schema_validation_success(self, mock_jsonschema):
        """Test JSON schema validation success."""
        # Mock jsonschema validation
        mock_jsonschema.validate.return_value = None  # No exception means valid
        
        # Create test JSON file
        test_file = self.temp_dir / "data.json"
        test_data = {"name": "test", "value": 42}
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            },
            "required": ["name", "value"]
        }
        
        validation = CaseValidation(
            type="json_schema",
            target="data.json",
            validation_schema=schema
        )
        execution_result = {}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
        assert "validates against schema" in result.message
        mock_jsonschema.validate.assert_called_once()
    
    @patch('dact.validation_engine.jsonschema')
    def test_json_schema_validation_failure(self, mock_jsonschema):
        """Test JSON schema validation failure."""
        from jsonschema import ValidationError
        
        # Mock jsonschema validation to raise error
        mock_jsonschema.validate.side_effect = ValidationError("'name' is a required property")
        mock_jsonschema.ValidationError = ValidationError
        
        # Create test JSON file
        test_file = self.temp_dir / "invalid.json"
        test_data = {"value": 42}  # Missing required 'name' field
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            },
            "required": ["name", "value"]
        }
        
        validation = CaseValidation(
            type="json_schema",
            target="invalid.json",
            validation_schema=schema
        )
        execution_result = {}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert not result.is_valid
        assert "JSON schema validation failed" in result.message
    
    def test_numeric_range_validation_success(self):
        """Test numeric range validation success."""
        validation = CaseValidation(
            type="numeric_range",
            target="score",
            min_value=0.0,
            max_value=100.0
        )
        execution_result = {
            "outputs": {
                "score": "85.5"  # String that can be converted to float
            }
        }
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
        assert "within acceptable range" in result.message
    
    def test_numeric_range_validation_failure(self):
        """Test numeric range validation failure."""
        validation = CaseValidation(
            type="numeric_range",
            target="temperature",
            min_value=-10.0,
            max_value=50.0
        )
        execution_result = {
            "outputs": {
                "temperature": 75.0  # Above maximum
            }
        }
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert not result.is_valid
        assert "above maximum 50.0" in result.message
    
    def test_numeric_range_validation_non_numeric(self):
        """Test numeric range validation with non-numeric value."""
        validation = CaseValidation(
            type="numeric_range",
            target="result",
            min_value=0.0,
            max_value=100.0
        )
        execution_result = {
            "outputs": {
                "result": "not_a_number"
            }
        }
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert not result.is_valid
        assert "not a numeric value" in result.message
    
    def test_custom_validation_with_registration(self):
        """Test custom validation with registered validator."""
        def custom_validator(validation, execution_result, work_dir):
            # Custom logic: check if output contains specific pattern
            outputs = execution_result.get("outputs", {})
            target_value = outputs.get(validation.target, "")
            
            if "SUCCESS" in target_value:
                return ValidationResult(True, "Custom validation passed: SUCCESS found")
            else:
                return ValidationResult(False, "Custom validation failed: SUCCESS not found")
        
        # Register the custom validator
        self.engine.register_custom_validator("check_success", custom_validator)
        
        validation = CaseValidation(
            type="custom",
            target="result",
            custom_validator="check_success"
        )
        execution_result = {
            "outputs": {
                "result": "Operation completed: SUCCESS"
            }
        }
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
        assert "Custom validation passed: SUCCESS found" in result.message
    
    def test_validation_with_description(self):
        """Test that validation descriptions are properly handled."""
        validation = CaseValidation(
            type="exit_code",
            expected=0,
            description="Verify successful command execution"
        )
        execution_result = {"returncode": 0}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
        # The description should be used in logging, not in the result message
        assert validation.description == "Verify successful command execution"
    
    def test_unknown_validation_type_handling(self):
        """Test handling of unknown validation types."""
        validation = CaseValidation(
            type="unknown_validation_type",
            target="something"
        )
        execution_result = {}
        
        result = self.engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert not result.is_valid
        assert "Unknown validation type: unknown_validation_type" in result.message


class TestValidationEngineIntegration:
    """Test validation engine integration with multiple validations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ValidationEngine()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_multiple_validations_all_pass(self):
        """Test multiple validations where all pass."""
        # Create test file
        test_file = self.temp_dir / "output.txt"
        test_file.write_text("Process completed successfully")
        
        validations = [
            CaseValidation(type="exit_code", expected=0, description="Check exit code"),
            CaseValidation(type="file_exists", target="output.txt", description="Check output file"),
            CaseValidation(type="stdout_contains", expected="success", description="Check success message")
        ]
        
        execution_result = {
            "returncode": 0,
            "stdout": "Operation completed with success"
        }
        
        results = self.engine.validate_case(validations, execution_result, self.temp_dir)
        
        assert len(results) == 3
        assert all(r.is_valid for r in results)
    
    def test_multiple_validations_some_fail(self):
        """Test multiple validations where some fail."""
        validations = [
            CaseValidation(type="exit_code", expected=0, description="Check exit code"),
            CaseValidation(type="file_exists", target="missing.txt", description="Check missing file"),
            CaseValidation(type="stdout_contains", expected="success", description="Check success message")
        ]
        
        execution_result = {
            "returncode": 0,
            "stdout": "Operation completed with success"
        }
        
        results = self.engine.validate_case(validations, execution_result, self.temp_dir)
        
        assert len(results) == 3
        assert results[0].is_valid  # exit_code passes
        assert not results[1].is_valid  # file_exists fails
        assert results[2].is_valid  # stdout_contains passes
    
    def test_validation_exception_handling(self):
        """Test that validation exceptions are properly handled."""
        # Create a validation that will cause an exception
        validation = CaseValidation(
            type="file_content",
            target="nonexistent.txt",
            expected="some content"
        )
        
        execution_result = {}
        
        results = self.engine.validate_case([validation], execution_result, self.temp_dir)
        
        assert len(results) == 1
        assert not results[0].is_valid
        assert "does not exist" in results[0].message


if __name__ == "__main__":
    pytest.main([__file__])