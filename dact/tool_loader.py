import yaml
from pathlib import Path
from typing import Dict
from dact.models import Tool

class ToolLoader:
    """
    Loads and validates tool definitions from YAML files.
    """
    def __init__(self, tool_directory: Path):
        self.tool_directory = tool_directory
        self._tools: Dict[str, Tool] = {}

    def load_tools(self) -> Dict[str, Tool]:
        """
        Scans the tool directory, loads, validates, and returns the tools.
        """
        if not self.tool_directory.is_dir():
            # In the future, we might want to handle this with logging
            return {}

        for tool_file in self.tool_directory.glob("*.tool.yml"):
            with open(tool_file, 'r') as f:
                tool_data = yaml.safe_load(f)
                if tool_data:
                    tool = Tool(**tool_data)
                    if tool.name in self._tools:
                        # Handle duplicate tool names, maybe raise an error
                        pass
                    self._tools[tool.name] = tool
        return self._tools

def load_tools_from_directory(directory: str) -> Dict[str, Tool]:
    """
    Scans a directory for *.tool.yml files, validates them, and returns a
    dictionary of Tool objects.
    """
    loader = ToolLoader(Path(directory))
    return loader.load_tools()
