import yaml
from pathlib import Path
from typing import Dict
from dact.models import Scenario

def load_scenarios_from_directory(directory: str) -> Dict[str, Scenario]:
    """
    Scans a directory for *.scenario.yml files, validates them, and returns a
    dictionary of Scenario objects.
    """
    scenario_dir = Path(directory)
    scenarios: Dict[str, Scenario] = {}
    if not scenario_dir.is_dir():
        return scenarios

    for scenario_file in scenario_dir.glob("*.scenario.yml"):
        with open(scenario_file, 'r') as f:
            scenario_data = yaml.safe_load(f)
            if scenario_data:
                scenario = Scenario(**scenario_data)
                if scenario.name in scenarios:
                    # Handle duplicate scenario names
                    pass
                scenarios[scenario.name] = scenario
    return scenarios
