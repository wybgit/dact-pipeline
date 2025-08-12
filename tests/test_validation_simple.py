"""
Simple tests for validation functionality.
"""
import pytest
from dact.models import CaseValidation
from dact.validation_engine import ValidationEngine, ValidationResult


def test_case_validation_model():
    """Test CaseValidation model creation."""
    validation = CaseValidation(
        type="exit_code",
        expected=0,
        description="Check successful execution"
    )
    assert validation.type == "exit_code"
    assert validation.expected == 0
    assert validation.description == "Check successful execution"


def test_validation_engine_exit_code():
    """Test ValidationEngine exit code validation."""
    engine = ValidationEngine()
    validation = CaseValidation(type="exit_code", expected=0)
    execution_result = {"returncode": 0}
    
    result = engine._execute_validation(validation, execution_result, None)
    
    assert result.is_valid
    assert "Expected exit code 0, got 0" in result.message


def test_validation_engine_stdout_contains():
    """Test ValidationEngine stdout contains validation."""
    engine = ValidationEngine()
    validation = CaseValidation(type="stdout_contains", expected="success")
    execution_result = {"stdout": "Operation completed successfully"}
    
    result = engine._execute_validation(validation, execution_result, None)
    
    assert result.is_valid