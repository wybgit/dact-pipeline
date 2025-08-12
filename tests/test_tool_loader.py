import pytest
from pathlib import Path
from dact.tool_loader import load_tools_from_directory

@pytest.fixture
def tool_dir(tmp_path: Path) -> Path:
    """Creates a temporary directory with sample tool files for testing."""
    d = tmp_path / "tools"
    d.mkdir()
    
    # Valid tool file
    tool1_content = """
name: echo-tool
command_template: echo "hello"
"""
    (d / "echo.tool.yml").write_text(tool1_content)

    # Another valid tool file
    tool2_content = """
name: ls-tool
description: "Lists files"
command_template: ls -l
parameters:
    path:
        type: str
        default: "."
"""
    (d / "ls.tool.yml").write_text(tool2_content)

    # Invalid tool file (missing name)
    invalid_tool_content = """
command_template: "some command"
"""
    (d / "invalid.tool.yml").write_text(invalid_tool_content)
    
    # A non-tool yaml file
    (d / "data.yml").write_text("key: value")

    return d

def test_load_tools_from_directory(tool_dir: Path):
    """
    Tests that tools are loaded correctly from a directory.
    """
    # The invalid tool file should raise a validation error,
    # which we expect to be handled gracefully (e.g., skipped).
    # For now, let's assume it raises an error.
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        load_tools_from_directory(str(tool_dir))

    # Let's fix the invalid file and try again
    (tool_dir / "invalid.tool.yml").write_text("name: invalid-tool\ncommand_template: 'some command'")
    
    tools = load_tools_from_directory(str(tool_dir))
    
    assert len(tools) == 3
    assert "echo-tool" in tools
    assert "ls-tool" in tools
    assert "invalid-tool" in tools
    
    assert tools["ls-tool"].description == "Lists files"
    assert tools["ls-tool"].parameters["path"].default == "."

def test_load_tools_from_nonexistent_directory():
    """
    Tests that loading from a non-existent directory returns an empty dict.
    """
    tools = load_tools_from_directory("non_existent_dir")
    assert len(tools) == 0
