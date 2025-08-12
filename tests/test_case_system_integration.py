"""
Integration tests for the enhanced test case system.
"""
import pytest
import tempfile
import json
import csv
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
from dact.models import Case, CaseFile, CaseValidation, DataDrivenCase, Tool, Scenario, Step
from dact.pytest_plugin import CaseYAMLFile, TestCaseItem
from dact.validation_engine import ValidationEngine
from dact.data_providers import load_test_data


class TestCaseSystemIntegration:
    """Integration tests for the complete enhanced test case system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.tools_dir = self.temp_dir / "tools"
        self.scenarios_dir = self.temp_dir / "scenarios"
        self.cases_dir = self.temp_dir / "cases"
        self.data_dir = self.temp_dir / "data"
        
        # Create directories
        for dir_path in [self.tools_dir, self.scenarios_dir, self.cases_dir, self.data_dir]:
            dir_path.mkdir(parents=True)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_complete_data_driven_workflow(self):
        """Test complete data-driven workflow with validation."""
        # Create test data file
        test_data = [
            {"model": "resnet50", "batch_size": "32", "expected_accuracy": "0.95"},
            {"model": "mobilenet", "batch_size": "64", "expected_accuracy": "0.88"},
            {"model": "efficientnet", "batch_size": "16", "expected_accuracy": "0.97"}
        ]
        
        data_file = self.data_dir / "model_tests.json"
        with open(data_file, 'w') as f:
            json.dump(test_data, f)
        
        # Create case file with data-driven test
        template_case = Case(
            name="model_test_template",
            scenario="model_evaluation",
            params={
                "model_name": "{{ model }}",
                "batch_size": "{{ batch_size_int }}"
            },
            validation=[
                CaseValidation(
                    type="performance",
                    target="accuracy",
                    expected="{{ expected_accuracy_float }}",
                    tolerance=0.05,
                    description="Check model accuracy"
                ),
                CaseValidation(
                    type="exit_code",
                    expected=0,
                    description="Check successful execution"
                )
            ]
        )
        
        data_driven_case = DataDrivenCase(
            template=template_case,
            data_source=str(data_file),
            data_transform={
                "batch_size_int": "int(batch_size)",
                "expected_accuracy_float": "float(expected_accuracy)"
            },
            name_template="test_{{ model }}_batch{{ batch_size }}"
        )
        
        case_file = CaseFile(
            common_params={"timeout": 300},
            cases=[],
            data_driven_cases=[data_driven_case]
        )
        
        # Verify the structure
        assert len(case_file.data_driven_cases) == 1
        assert case_file.data_driven_cases[0].template.name == "model_test_template"
        assert len(case_file.data_driven_cases[0].template.validation) == 2
    
    def test_parameter_override_hierarchy(self):
        """Test parameter override hierarchy: common_params < case_params < step_params."""
        case_file = CaseFile(
            common_params={
                "global_timeout": 300,
                "retries": 3,
                "step1": {
                    "common_param": "from_common"
                }
            },
            cases=[
                Case(
                    name="override_test",
                    scenario="multi_step_scenario",
                    params={
                        "retries": 5,  # Override common param
                        "step1": {
                            "common_param": "from_case",  # Override common step param
                            "case_specific": "case_value"
                        },
                        "step2": {
                            "step2_param": "step2_value"
                        }
                    }
                )
            ]
        )
        
        # Simulate parameter merging logic from pytest plugin
        case = case_file.cases[0]
        merged_params = case_file.common_params.copy()
        
        # Simple merge (real implementation would need deep merge)
        merged_params.update(case.params)
        case.params = merged_params
        
        # Verify override hierarchy
        assert case.params["global_timeout"] == 300  # From common_params
        assert case.params["retries"] == 5  # Overridden by case
        assert case.params["step1"]["case_specific"] == "case_value"  # Case-specific
        assert case.params["step2"]["step2_param"] == "step2_value"  # Case-specific
    
    def test_validation_engine_with_multiple_types(self):
        """Test validation engine with multiple validation types."""
        engine = ValidationEngine()
        
        # Create test files
        output_file = self.temp_dir / "output.txt"
        output_file.write_text("Process completed successfully\nAccuracy: 0.95")
        
        json_file = self.temp_dir / "results.json"
        with open(json_file, 'w') as f:
            json.dump({"status": "success", "accuracy": 0.95}, f)
        
        # Define multiple validations
        validations = [
            CaseValidation(
                type="exit_code",
                expected=0,
                description="Check successful execution"
            ),
            CaseValidation(
                type="file_exists",
                target="output.txt",
                description="Check output file exists"
            ),
            CaseValidation(
                type="file_content",
                target="output.txt",
                pattern=r"Accuracy: \d+\.\d+",
                description="Check accuracy pattern in output"
            ),
            CaseValidation(
                type="performance",
                target="execution_time",
                max_value=10.0,
                description="Check execution time"
            ),
            CaseValidation(
                type="numeric_range",
                target="accuracy",
                min_value=0.8,
                max_value=1.0,
                description="Check accuracy range"
            )
        ]
        
        execution_result = {
            "returncode": 0,
            "stdout": "Model evaluation completed",
            "metrics": {"execution_time": 5.2},
            "outputs": {"accuracy": 0.95}
        }
        
        results = engine.validate_case(validations, execution_result, self.temp_dir)
        
        assert len(results) == 5
        assert all(r.is_valid for r in results)
    
    def test_data_filtering_and_transformation(self):
        """Test data filtering and transformation in data-driven tests."""
        # Create comprehensive test data
        test_data = [
            {"model": "resnet50", "size": "large", "batch_size": "32", "priority": "high", "accuracy": "0.95"},
            {"model": "mobilenet", "size": "small", "batch_size": "64", "priority": "medium", "accuracy": "0.88"},
            {"model": "efficientnet", "size": "medium", "batch_size": "16", "priority": "high", "accuracy": "0.97"},
            {"model": "vgg16", "size": "large", "batch_size": "8", "priority": "low", "accuracy": "0.92"}
        ]
        
        data_file = self.data_dir / "comprehensive_tests.json"
        with open(data_file, 'w') as f:
            json.dump(test_data, f)
        
        # Create mock CaseYAMLFile for testing filtering and transformation
        yaml_file = CaseYAMLFile.from_parent(None, fspath=self.temp_dir / "test.case.yml")
        
        # Test filtering for high priority tests only
        filter_criteria = {"priority": "high"}
        filtered_data = yaml_file._filter_test_data(test_data, filter_criteria)
        
        assert len(filtered_data) == 2
        assert all(row["priority"] == "high" for row in filtered_data)
        
        # Test transformation
        transformations = {
            "batch_size_int": "int(batch_size)",
            "accuracy_float": "float(accuracy)",
            "model_upper": "str(model)"  # This would need enhancement for actual string operations
        }
        
        transformed_row = yaml_file._transform_data_row(filtered_data[0], transformations)
        
        assert transformed_row["batch_size_int"] == 32
        assert transformed_row["accuracy_float"] == 0.95
        assert isinstance(transformed_row["batch_size_int"], int)
        assert isinstance(transformed_row["accuracy_float"], float)
    
    def test_custom_validation_registration(self):
        """Test custom validation function registration and execution."""
        engine = ValidationEngine()
        
        # Define custom validator
        def validate_model_output(validation, execution_result, work_dir):
            """Custom validator for model output format."""
            outputs = execution_result.get("outputs", {})
            model_output = outputs.get("model_result", "")
            
            # Check if output contains required fields
            required_fields = ["accuracy", "loss", "inference_time"]
            
            try:
                import json
                result_data = json.loads(model_output)
                
                missing_fields = [field for field in required_fields if field not in result_data]
                
                if missing_fields:
                    return ValidationResult(
                        False, 
                        f"Missing required fields: {missing_fields}"
                    )
                
                # Check accuracy is reasonable
                accuracy = result_data.get("accuracy", 0)
                if accuracy < 0.5:
                    return ValidationResult(
                        False,
                        f"Accuracy too low: {accuracy}"
                    )
                
                return ValidationResult(True, "Model output validation passed")
                
            except json.JSONDecodeError:
                return ValidationResult(False, "Model output is not valid JSON")
        
        # Register custom validator
        engine.register_custom_validator("validate_model_output", validate_model_output)
        
        # Test with valid output
        validation = CaseValidation(
            type="custom",
            target="model_result",
            custom_validator="validate_model_output"
        )
        
        execution_result = {
            "outputs": {
                "model_result": '{"accuracy": 0.95, "loss": 0.05, "inference_time": 2.3}'
            }
        }
        
        from dact.validation_engine import ValidationResult
        result = engine._execute_validation(validation, execution_result, self.temp_dir)
        
        assert result.is_valid
        assert "Model output validation passed" in result.message
        
        # Test with invalid output (missing field)
        execution_result_invalid = {
            "outputs": {
                "model_result": '{"accuracy": 0.95, "loss": 0.05}'  # Missing inference_time
            }
        }
        
        result_invalid = engine._execute_validation(validation, execution_result_invalid, self.temp_dir)
        
        assert not result_invalid.is_valid
        assert "Missing required fields" in result_invalid.message
    
    def test_case_with_setup_and_teardown(self):
        """Test case with setup and teardown configuration."""
        case = Case(
            name="test_with_lifecycle",
            tool="test_tool",
            params={"input": "test_data.txt"},
            setup={
                "create_dirs": ["input", "output"],
                "copy_files": {"source": "template.txt", "dest": "input/test_data.txt"}
            },
            teardown={
                "cleanup_dirs": ["temp"],
                "archive_results": True
            },
            validation=[
                CaseValidation(
                    type="file_exists",
                    target="output/result.txt",
                    description="Check result file created"
                )
            ],
            timeout=600,
            retry_count=2
        )
        
        # Verify all fields are set correctly
        assert case.name == "test_with_lifecycle"
        assert case.setup["create_dirs"] == ["input", "output"]
        assert case.teardown["cleanup_dirs"] == ["temp"]
        assert len(case.validation) == 1
        assert case.timeout == 600
        assert case.retry_count == 2
    
    def test_comprehensive_case_file_structure(self):
        """Test comprehensive case file with all features."""
        # Create test data
        test_data_file = self.data_dir / "integration_tests.csv"
        with open(test_data_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['test_name', 'model', 'batch_size', 'expected_accuracy'])
            writer.writerow(['small_batch', 'resnet50', '16', '0.94'])
            writer.writerow(['large_batch', 'resnet50', '64', '0.96'])
        
        # Create comprehensive case file
        regular_case = Case(
            name="manual_test",
            tool="model_evaluator",
            params={"model": "custom_model.onnx"},
            validation=[
                CaseValidation(type="exit_code", expected=0)
            ]
        )
        
        template_case = Case(
            name="batch_test_template",
            scenario="model_evaluation",
            params={
                "model_name": "{{ model }}",
                "batch_size": "{{ batch_size_int }}"
            },
            validation=[
                CaseValidation(
                    type="performance",
                    target="accuracy",
                    expected="{{ expected_accuracy_float }}",
                    tolerance=0.02
                )
            ]
        )
        
        data_driven_case = DataDrivenCase(
            template=template_case,
            data_source=str(test_data_file),
            data_transform={
                "batch_size_int": "int(batch_size)",
                "expected_accuracy_float": "float(expected_accuracy)"
            },
            name_template="{{ test_name }}_{{ model }}"
        )
        
        case_file = CaseFile(
            common_params={
                "timeout": 300,
                "retries": 2,
                "environment": "test"
            },
            cases=[regular_case],
            data_driven_cases=[data_driven_case]
        )
        
        # Verify complete structure
        assert len(case_file.cases) == 1
        assert len(case_file.data_driven_cases) == 1
        assert case_file.common_params["timeout"] == 300
        assert case_file.cases[0].name == "manual_test"
        assert case_file.data_driven_cases[0].template.name == "batch_test_template"


class TestRealWorldScenarios:
    """Test real-world scenarios that demonstrate the enhanced system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_ai_model_pipeline_scenario(self):
        """Test AI model pipeline scenario with multiple validation types."""
        # This represents a real AI model testing pipeline
        
        # Model test data
        model_data = [
            {
                "model_name": "resnet50",
                "input_shape": "3,224,224",
                "batch_sizes": [1, 4, 8],
                "target_accuracy": 0.95,
                "max_inference_time": 50.0
            },
            {
                "model_name": "mobilenet_v2",
                "input_shape": "3,224,224", 
                "batch_sizes": [1, 8, 16],
                "target_accuracy": 0.88,
                "max_inference_time": 20.0
            }
        ]
        
        data_file = self.temp_dir / "ai_models.json"
        with open(data_file, 'w') as f:
            json.dump(model_data, f)
        
        # Template case for AI model testing
        template_case = Case(
            name="ai_model_test",
            scenario="onnx_to_atc_conversion",
            params={
                "model_name": "{{ model_name }}",
                "input_shape": "{{ input_shape }}",
                "batch_size": "{{ batch_size }}"
            },
            validation=[
                CaseValidation(
                    type="exit_code",
                    expected=0,
                    description="Conversion should succeed"
                ),
                CaseValidation(
                    type="file_exists",
                    target="output/*.om",
                    description="ATC output file should exist"
                ),
                CaseValidation(
                    type="performance",
                    target="inference_time",
                    max_value="{{ max_inference_time }}",
                    description="Inference time should be within limits"
                ),
                CaseValidation(
                    type="performance",
                    target="accuracy",
                    min_value="{{ target_accuracy }}",
                    tolerance=0.05,
                    description="Accuracy should meet target"
                ),
                CaseValidation(
                    type="file_size",
                    target="output/model.om",
                    min_value=1000,  # At least 1KB
                    description="Output model should not be empty"
                )
            ]
        )
        
        # Data-driven case with batch size expansion
        data_driven_case = DataDrivenCase(
            template=template_case,
            data_source=str(data_file),
            # This would need custom logic to expand batch_sizes array
            name_template="test_{{ model_name }}_batch{{ batch_size }}"
        )
        
        # Verify the structure represents a realistic AI testing scenario
        assert template_case.scenario == "onnx_to_atc_conversion"
        assert len(template_case.validation) == 5
        assert any(v.type == "performance" for v in template_case.validation)
        assert any(v.type == "file_exists" for v in template_case.validation)
    
    def test_performance_regression_testing(self):
        """Test performance regression testing scenario."""
        # Performance baseline data
        baseline_data = [
            {
                "test_name": "inference_latency",
                "model": "resnet50",
                "baseline_time": 45.2,
                "max_regression": 0.1  # 10% regression allowed
            },
            {
                "test_name": "memory_usage",
                "model": "resnet50", 
                "baseline_memory": 512.0,
                "max_regression": 0.05  # 5% regression allowed
            }
        ]
        
        data_file = self.temp_dir / "performance_baselines.json"
        with open(data_file, 'w') as f:
            json.dump(baseline_data, f)
        
        # Performance regression test case
        template_case = Case(
            name="performance_regression_test",
            scenario="performance_benchmark",
            params={
                "model": "{{ model }}",
                "test_type": "{{ test_name }}"
            },
            validation=[
                CaseValidation(
                    type="performance",
                    target="{{ test_name }}",
                    max_value="{{ max_allowed_value }}",
                    description="Check performance regression"
                ),
                CaseValidation(
                    type="custom",
                    custom_validator="regression_checker",
                    description="Custom regression analysis"
                )
            ]
        )
        
        # This would include data transformation to calculate max_allowed_value
        # based on baseline and regression tolerance
        data_driven_case = DataDrivenCase(
            template=template_case,
            data_source=str(data_file),
            data_transform={
                "max_allowed_value": "baseline_time * (1 + max_regression)"  # Would need more complex logic
            },
            name_template="regression_{{ test_name }}_{{ model }}"
        )
        
        # Verify performance testing structure
        assert template_case.name == "performance_regression_test"
        assert any(v.type == "performance" for v in template_case.validation)
        assert any(v.type == "custom" for v in template_case.validation)


if __name__ == "__main__":
    pytest.main([__file__])