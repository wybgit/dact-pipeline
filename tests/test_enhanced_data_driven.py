"""
Tests for enhanced data-driven testing features.
"""
import pytest
import tempfile
import json
import csv
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
from dact.models import Case, CaseFile, DataDrivenCase, CaseValidation
from dact.pytest_plugin import CaseYAMLFile


class TestEnhancedDataDrivenFeatures:
    """Test enhanced data-driven testing features."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_data_filter_simple_equality(self):
        """Test data filtering with simple equality."""
        # Create mock CaseYAMLFile instance
        yaml_file = Mock()
        yaml_file._filter_test_data = CaseYAMLFile._filter_test_data.__get__(yaml_file, CaseYAMLFile)
        
        test_data = [
            {"name": "test1", "category": "unit", "priority": "high"},
            {"name": "test2", "category": "integration", "priority": "low"},
            {"name": "test3", "category": "unit", "priority": "medium"},
        ]
        
        filter_criteria = {"category": "unit"}
        
        filtered_data = yaml_file._filter_test_data(test_data, filter_criteria)
        
        assert len(filtered_data) == 2
        assert all(row["category"] == "unit" for row in filtered_data)
    
    def test_data_filter_complex_operations(self):
        """Test data filtering with complex operations."""
        yaml_file = Mock()
        yaml_file._filter_test_data = CaseYAMLFile._filter_test_data.__get__(yaml_file, CaseYAMLFile)
        
        test_data = [
            {"name": "test1", "score": 85, "category": "unit"},
            {"name": "test2", "score": 92, "category": "integration"},
            {"name": "test3", "score": 78, "category": "unit"},
            {"name": "test4", "score": 95, "category": "e2e"},
        ]
        
        # Filter for scores greater than 80 and less than 95
        filter_criteria = {
            "score": {"$gt": 80, "$lt": 95}
        }
        
        filtered_data = yaml_file._filter_test_data(test_data, filter_criteria)
        
        assert len(filtered_data) == 2
        assert all(80 < row["score"] < 95 for row in filtered_data)
    
    def test_data_filter_in_operation(self):
        """Test data filtering with $in operation."""
        yaml_file = Mock()
        yaml_file._filter_test_data = CaseYAMLFile._filter_test_data.__get__(yaml_file, CaseYAMLFile)
        
        test_data = [
            {"name": "test1", "platform": "linux"},
            {"name": "test2", "platform": "windows"},
            {"name": "test3", "platform": "macos"},
            {"name": "test4", "platform": "android"},
        ]
        
        filter_criteria = {
            "platform": {"$in": ["linux", "windows"]}
        }
        
        filtered_data = yaml_file._filter_test_data(test_data, filter_criteria)
        
        assert len(filtered_data) == 2
        assert all(row["platform"] in ["linux", "windows"] for row in filtered_data)
    
    def test_data_transform_type_conversion(self):
        """Test data transformation with type conversion."""
        yaml_file = Mock()
        yaml_file._transform_data_row = CaseYAMLFile._transform_data_row.__get__(yaml_file, CaseYAMLFile)
        
        data_row = {
            "batch_size": "32",
            "learning_rate": "0.001",
            "epochs": "100"
        }
        
        transformations = {
            "batch_size_int": "int(batch_size)",
            "learning_rate_float": "float(learning_rate)",
            "epochs_str": "str(epochs)"
        }
        
        transformed_row = yaml_file._transform_data_row(data_row, transformations)
        
        assert transformed_row["batch_size_int"] == 32
        assert transformed_row["learning_rate_float"] == 0.001
        assert transformed_row["epochs_str"] == "100"
        assert isinstance(transformed_row["batch_size_int"], int)
        assert isinstance(transformed_row["learning_rate_float"], float)
        assert isinstance(transformed_row["epochs_str"], str)
    
    def test_data_transform_arithmetic(self):
        """Test data transformation with arithmetic operations."""
        yaml_file = Mock()
        yaml_file._transform_data_row = CaseYAMLFile._transform_data_row.__get__(yaml_file, CaseYAMLFile)
        
        data_row = {
            "width": 224,
            "height": 224,
            "channels": 3
        }
        
        transformations = {
            "total_pixels": "width + height",  # Simple addition
            "input_shape": "channels"  # Simple mapping
        }
        
        transformed_row = yaml_file._transform_data_row(data_row, transformations)
        
        assert transformed_row["total_pixels"] == 448  # 224 + 224
        assert transformed_row["input_shape"] == 3
    
    def test_data_transform_literal_values(self):
        """Test data transformation with literal values."""
        yaml_file = Mock()
        yaml_file._transform_data_row = CaseYAMLFile._transform_data_row.__get__(yaml_file, CaseYAMLFile)
        
        data_row = {
            "model_name": "resnet50"
        }
        
        transformations = {
            "framework": "pytorch",  # Literal string
            "device": "cuda",        # Literal string
            "model": "model_name"    # Key mapping
        }
        
        transformed_row = yaml_file._transform_data_row(data_row, transformations)
        
        assert transformed_row["framework"] == "pytorch"
        assert transformed_row["device"] == "cuda"
        assert transformed_row["model"] == "resnet50"
    
    def test_case_name_template_rendering(self):
        """Test case name template rendering."""
        yaml_file = Mock()
        yaml_file._render_case_name = CaseYAMLFile._render_case_name.__get__(yaml_file, CaseYAMLFile)
        
        data_row = {
            "model": "resnet50",
            "batch_size": 32,
            "dataset": "imagenet"
        }
        
        name_template = "test_{{ model }}_batch{{ batch_size }}_{{ dataset }}"
        
        case_name = yaml_file._render_case_name(name_template, data_row, 0)
        
        assert case_name == "test_resnet50_batch32_imagenet"
    
    def test_case_name_template_with_index(self):
        """Test case name template rendering with index."""
        yaml_file = Mock()
        yaml_file._render_case_name = CaseYAMLFile._render_case_name.__get__(yaml_file, CaseYAMLFile)
        
        data_row = {
            "test_type": "performance"
        }
        
        name_template = "{{ test_type }}_test_{{ index }}"
        
        case_name = yaml_file._render_case_name(name_template, data_row, 5)
        
        assert case_name == "performance_test_5"
    
    def test_case_name_template_fallback(self):
        """Test case name template fallback on error."""
        yaml_file = Mock()
        yaml_file._render_case_name = CaseYAMLFile._render_case_name.__get__(yaml_file, CaseYAMLFile)
        
        data_row = {"model": "resnet50"}
        
        # Invalid template (missing variable)
        name_template = "test_{{ missing_variable }}"
        
        case_name = yaml_file._render_case_name(name_template, data_row, 3)
        
        assert case_name == "case_3"  # Fallback name


class TestDataDrivenCaseModel:
    """Test the enhanced DataDrivenCase model."""
    
    def test_enhanced_data_driven_case_model(self):
        """Test DataDrivenCase model with new features."""
        template_case = Case(
            name="template_test",
            scenario="test_scenario",
            params={"param1": "{{ data.value }}"}
        )
        
        data_driven_case = DataDrivenCase(
            template=template_case,
            data_source="test_data.csv",
            parameter_mapping={"param1": "value_column"},
            data_filter={"category": "unit"},
            data_transform={"batch_size_int": "int(batch_size)"},
            name_template="test_{{ data.name }}_{{ index }}"
        )
        
        assert data_driven_case.template.name == "template_test"
        assert data_driven_case.data_source == "test_data.csv"
        assert data_driven_case.parameter_mapping["param1"] == "value_column"
        assert data_driven_case.data_filter["category"] == "unit"
        assert data_driven_case.data_transform["batch_size_int"] == "int(batch_size)"
        assert data_driven_case.name_template == "test_{{ data.name }}_{{ index }}"
    
    def test_data_driven_case_optional_fields(self):
        """Test DataDrivenCase with optional fields."""
        template_case = Case(name="simple_test", tool="test_tool")
        
        data_driven_case = DataDrivenCase(
            template=template_case,
            data_source="simple_data.json"
        )
        
        assert data_driven_case.data_filter is None
        assert data_driven_case.data_transform is None
        assert data_driven_case.name_template is None
        assert data_driven_case.parameter_mapping == {}


class TestDataDrivenIntegrationScenarios:
    """Test realistic data-driven testing scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_model_testing_scenario(self):
        """Test a realistic model testing scenario with data-driven cases."""
        # Create test data file
        test_data_file = self.temp_dir / "model_tests.csv"
        with open(test_data_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['model_name', 'batch_size', 'input_size', 'expected_accuracy'])
            writer.writerow(['resnet50', '32', '224', '0.95'])
            writer.writerow(['mobilenet', '64', '224', '0.88'])
            writer.writerow(['efficientnet', '16', '256', '0.97'])
        
        # Create template case
        template_case = Case(
            name="model_accuracy_test",
            scenario="model_evaluation",
            params={
                "model": "{{ model_name }}",
                "batch_size": "{{ batch_size_int }}",
                "input_size": "{{ input_size_int }}"
            },
            validation=[
                CaseValidation(
                    type="performance",
                    target="accuracy",
                    min_value=0.8,
                    description="Check minimum accuracy"
                ),
                CaseValidation(
                    type="numeric_range",
                    target="accuracy",
                    expected="{{ expected_accuracy_float }}",
                    tolerance=0.05,
                    description="Check expected accuracy within tolerance"
                )
            ]
        )
        
        # Create data-driven case
        data_driven_case = DataDrivenCase(
            template=template_case,
            data_source=str(test_data_file),
            parameter_mapping={
                "model_name": "model_name",
                "batch_size_int": "batch_size",
                "input_size_int": "input_size",
                "expected_accuracy_float": "expected_accuracy"
            },
            data_transform={
                "batch_size_int": "int(batch_size)",
                "input_size_int": "int(input_size)",
                "expected_accuracy_float": "float(expected_accuracy)"
            },
            name_template="test_{{ model_name }}_batch{{ batch_size }}"
        )
        
        # Verify the model structure
        assert data_driven_case.template.name == "model_accuracy_test"
        assert len(data_driven_case.template.validation) == 2
        assert data_driven_case.name_template == "test_{{ model_name }}_batch{{ batch_size }}"
    
    def test_performance_testing_scenario(self):
        """Test a performance testing scenario with filtering."""
        # Create performance test data
        test_data = [
            {"test_name": "small_model", "input_size": 224, "iterations": 1000, "priority": "high"},
            {"test_name": "medium_model", "input_size": 512, "iterations": 500, "priority": "medium"},
            {"test_name": "large_model", "input_size": 1024, "iterations": 100, "priority": "low"},
            {"test_name": "huge_model", "input_size": 2048, "iterations": 50, "priority": "low"}
        ]
        
        test_data_file = self.temp_dir / "performance_tests.json"
        with open(test_data_file, 'w') as f:
            json.dump(test_data, f)
        
        # Create template case for performance testing
        template_case = Case(
            name="performance_test",
            scenario="benchmark_model",
            params={
                "input_size": "{{ input_size }}",
                "iterations": "{{ iterations }}"
            },
            validation=[
                CaseValidation(
                    type="performance",
                    target="avg_inference_time",
                    max_value=100.0,  # Max 100ms per inference
                    description="Check inference time performance"
                )
            ]
        )
        
        # Create data-driven case with filtering for high priority tests only
        data_driven_case = DataDrivenCase(
            template=template_case,
            data_source=str(test_data_file),
            data_filter={"priority": "high"},  # Only run high priority tests
            name_template="perf_{{ test_name }}"
        )
        
        # Verify the configuration
        assert data_driven_case.data_filter["priority"] == "high"
        assert data_driven_case.name_template == "perf_{{ test_name }}"


class TestParameterOverrideEnhancements:
    """Test enhanced parameter override mechanisms."""
    
    def test_nested_parameter_override(self):
        """Test nested parameter override for step-specific parameters."""
        case = Case(
            name="nested_override_test",
            scenario="multi_step_scenario",
            params={
                "global_timeout": 300,
                "step1": {
                    "model_path": "/path/to/model1.onnx",
                    "batch_size": 32
                },
                "step2": {
                    "output_format": "json",
                    "precision": "fp16"
                }
            }
        )
        
        # Verify nested structure
        assert case.params["global_timeout"] == 300
        assert case.params["step1"]["model_path"] == "/path/to/model1.onnx"
        assert case.params["step1"]["batch_size"] == 32
        assert case.params["step2"]["output_format"] == "json"
        assert case.params["step2"]["precision"] == "fp16"
    
    def test_common_params_with_nested_override(self):
        """Test common params with nested parameter override."""
        case_file = CaseFile(
            common_params={
                "timeout": 60,
                "retries": 3,
                "step1": {
                    "common_param": "common_value"
                }
            },
            cases=[
                Case(
                    name="test_with_nested_override",
                    scenario="test_scenario",
                    params={
                        "step1": {
                            "specific_param": "specific_value",
                            "common_param": "overridden_value"  # Override common param
                        }
                    }
                )
            ]
        )
        
        # Simulate parameter merging (this would be done by pytest plugin)
        case = case_file.cases[0]
        
        # Deep merge logic would be needed in the actual implementation
        # For now, just verify the structure is correct
        assert case_file.common_params["step1"]["common_param"] == "common_value"
        assert case.params["step1"]["common_param"] == "overridden_value"
        assert case.params["step1"]["specific_param"] == "specific_value"


if __name__ == "__main__":
    pytest.main([__file__])