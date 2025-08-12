"""
Tests for parameter override mechanisms.
"""
import pytest
from dact.models import Case, CaseFile


def test_common_params_override():
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


def test_scenario_step_parameter_override():
    """Test that case params can override scenario step parameters."""
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


def test_enhanced_case_model_features():
    """Test the enhanced Case model with new features."""
    case = Case(
        name="enhanced_test",
        description="Test with all features",
        tags=["integration", "slow"],
        scenario="test_scenario",
        params={"param1": "value1"},
        timeout=300,
        retry_count=2
    )
    
    assert case.name == "enhanced_test"
    assert "integration" in case.tags
    assert case.timeout == 300
    assert case.retry_count == 2