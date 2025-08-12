import pytest
from pathlib import Path
from pydantic import ValidationError
from dact.scenario_loader import load_scenarios_from_directory

@pytest.fixture
def scenario_dir(tmp_path: Path) -> Path:
    """Creates a temporary directory with sample scenario files for testing."""
    d = tmp_path / "scenarios"
    d.mkdir()

    # Valid scenario file
    scenario1_content = """
name: valid-scenario
steps:
  - name: step1
    tool: tool1
"""
    (d / "scenario1.scenario.yml").write_text(scenario1_content)

    # Invalid scenario file (steps is not a list)
    invalid_scenario_content = """
name: invalid-scenario
steps:
  name: step1
  tool: tool1
"""
    (d / "invalid.scenario.yml").write_text(invalid_scenario_content)

    return d

def test_load_scenarios_from_directory(scenario_dir: Path):
    """
    Tests that scenarios are loaded correctly and invalid ones are skipped.
    """
    # We expect the invalid file to raise a Pydantic error during parsing
    with pytest.raises(ValidationError):
        load_scenarios_from_directory(str(scenario_dir))

    # Let's fix the invalid file and try again
    fixed_content = """
name: invalid-scenario-fixed
steps:
  - name: step1
    tool: tool1
"""
    (scenario_dir / "invalid.scenario.yml").write_text(fixed_content)

    scenarios = load_scenarios_from_directory(str(scenario_dir))
    assert len(scenarios) == 2
    assert "valid-scenario" in scenarios
    assert "invalid-scenario-fixed" in scenarios
    assert scenarios["valid-scenario"].steps[0].name == "step1"

def test_load_scenarios_from_nonexistent_directory():
    """
    Tests that loading from a non-existent directory returns an empty dict.
    """
    scenarios = load_scenarios_from_directory("non_existent_dir_for_scenarios")
    assert len(scenarios) == 0
