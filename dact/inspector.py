"""
DACT Inspector - provides inspection and listing functionality for tools, scenarios, and cases.
"""
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel

from dact.models import Tool, Scenario, Case, CaseFile
from dact.tool_loader import load_tools_from_directory
from dact.scenario_loader import load_scenarios_from_directory


class ToolInfo(BaseModel):
    """Tool information model for display purposes."""
    name: str
    type: str
    description: Optional[str]
    command_template: str
    parameters: Dict[str, str]  # Simplified parameter info for display


class ScenarioPipeline(BaseModel):
    """Scenario pipeline information model."""
    name: str
    description: Optional[str]
    steps: List[Dict[str, str]]  # Simplified step info for display
    dependencies: Dict[str, List[str]]


class CaseInfo(BaseModel):
    """Case information model for display purposes."""
    name: str
    description: Optional[str]
    scenario: Optional[str]
    tool: Optional[str]
    source_file: str


class DACTInspector:
    """DACT Inspector - provides checking and listing functionality."""
    
    def __init__(self, tools_dir: str = "tools", scenarios_dir: str = "scenarios"):
        self.tools_dir = tools_dir
        self.scenarios_dir = scenarios_dir
    
    def list_tools(self) -> List[ToolInfo]:
        """List all registered tools and command templates."""
        tools = load_tools_from_directory(self.tools_dir)
        tool_infos = []
        
        for tool in tools.values():
            # Simplify parameters for display
            params_info = {}
            for param_name, param in tool.parameters.items():
                param_desc = f"{param.type}"
                if param.required:
                    param_desc += " (required)"
                if param.default is not None:
                    param_desc += f" = {param.default}"
                if param.help:
                    param_desc += f" - {param.help}"
                params_info[param_name] = param_desc
            
            tool_infos.append(ToolInfo(
                name=tool.name,
                type=tool.type,
                description=tool.description,
                command_template=tool.command_template,
                parameters=params_info
            ))
        
        return tool_infos
    
    def show_scenario_pipeline(self, scenario_name: str) -> ScenarioPipeline:
        """Show the pipeline diagram for a specified scenario."""
        scenarios = load_scenarios_from_directory(self.scenarios_dir)
        scenario = scenarios.get(scenario_name)
        
        if not scenario:
            raise ValueError(f"Scenario '{scenario_name}' not found")
        
        # Simplify steps for display
        steps_info = []
        for step in scenario.steps:
            step_info = {
                "name": step.name,
                "tool": step.tool,
                "description": step.description or ""
            }
            steps_info.append(step_info)
        
        # Extract dependencies (for now, just based on step order)
        dependencies = {}
        for i, step in enumerate(scenario.steps):
            if i > 0:
                # Simple dependency: each step depends on the previous one
                dependencies[step.name] = [scenario.steps[i-1].name]
            else:
                dependencies[step.name] = []
        
        return ScenarioPipeline(
            name=scenario.name,
            description=scenario.description,
            steps=steps_info,
            dependencies=dependencies
        )
    
    def list_cases(self, case_file: Optional[str] = None) -> List[CaseInfo]:
        """List test cases and their execution scenarios."""
        cases = []
        
        if case_file:
            # List cases from a specific file
            case_path = Path(case_file)
            if not case_path.exists():
                raise FileNotFoundError(f"Case file '{case_file}' not found")
            
            with open(case_path, 'r', encoding='utf-8') as f:
                case_data = yaml.safe_load(f)
            
            case_file_obj = CaseFile(**case_data)
            for case in case_file_obj.cases:
                cases.append(CaseInfo(
                    name=case.name,
                    description=case.description,
                    scenario=case.scenario,
                    tool=case.tool,
                    source_file=str(case_path)
                ))
        else:
            # List cases from all case files
            for case_file_path in Path(".").glob("**/*.case.yml"):
                try:
                    with open(case_file_path, 'r', encoding='utf-8') as f:
                        case_data = yaml.safe_load(f)
                    
                    case_file_obj = CaseFile(**case_data)
                    for case in case_file_obj.cases:
                        cases.append(CaseInfo(
                            name=case.name,
                            description=case.description,
                            scenario=case.scenario,
                            tool=case.tool,
                            source_file=str(case_file_path)
                        ))
                except Exception as e:
                    # Skip files that can't be parsed
                    print(f"Warning: Could not parse case file {case_file_path}: {e}")
                    continue
        
        return cases
    
    def _extract_dependencies(self, steps) -> Dict[str, List[str]]:
        """Extract dependencies from scenario steps."""
        # For now, implement simple sequential dependency
        dependencies = {}
        for i, step in enumerate(steps):
            if i > 0:
                dependencies[step.name] = [steps[i-1].name]
            else:
                dependencies[step.name] = []
        return dependencies