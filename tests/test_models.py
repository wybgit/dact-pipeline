import pytest
from pydantic import ValidationError
from dact.models import Tool, Scenario, Case, CaseFile

def test_tool_model_validation():
    """Tests the Tool model validation."""
    # Valid tool data
    valid_data = {
        "name": "my-tool",
        "command_template": "echo 'hello'",
        "parameters": {
            "message": {"type": "str", "required": True}
        }
    }
    tool = Tool(**valid_data)
    assert tool.name == "my-tool"
    assert tool.parameters["message"].required is True

    # Invalid tool data (missing required field)
    with pytest.raises(ValidationError):
        Tool(command_template="echo 'hello'")

def test_scenario_model_validation():
    """Tests the Scenario model validation."""
    valid_data = {
        "name": "my-scenario",
        "steps": [
            {"name": "step1", "tool": "my-tool", "params": {"message": "world"}}
        ]
    }
    scenario = Scenario(**valid_data)
    assert scenario.name == "my-scenario"
    assert len(scenario.steps) == 1
    assert scenario.steps[0].name == "step1"

    # Invalid scenario data (missing steps)
    with pytest.raises(ValidationError):
        Scenario(name="my-scenario")

def test_case_file_model_validation():
    """Tests the CaseFile and Case models validation."""
    valid_data = {
        "common_params": {"retries": 3},
        "cases": [
            {
                "name": "my-case",
                "scenario": "my-scenario",
                "params": {"step1": {"message": "override"}}
            }
        ]
    }
    case_file = CaseFile(**valid_data)
    assert case_file.common_params["retries"] == 3
    assert len(case_file.cases) == 1
    assert case_file.cases[0].name == "my-case"
    assert case_file.cases[0].scenario == "my-scenario"

    # Invalid case data (missing name)
    with pytest.raises(ValidationError):
        CaseFile(cases=[{"scenario": "my-scenario"}])
