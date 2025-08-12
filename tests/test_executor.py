import pytest
from pathlib import Path
from dact.models import Tool
from dact.executor import Executor

@pytest.fixture
def executor_tool() -> Tool:
    """A sample tool for executor tests."""
    tool_data = {
        "name": "command-tool",
        "command_template": "echo 'Hello, {{ name }}!' > {{ file }}",
        "post_exec": {
            "outputs": {
                "found_file": "find_file(dir='.', pattern='{{ file }}')"
            }
        }
    }
    return Tool(**tool_data)

def test_executor_post_exec_success(executor_tool: Tool, tmp_path: Path):
    """
    Tests that the Executor's post_exec hook successfully finds a file.
    """
    params = {"name": "World", "file": "output.txt"}
    executor = Executor(tool=executor_tool, params=params)
    result = executor.execute(work_dir=tmp_path)

    assert result["returncode"] == 0
    assert "found_file" in result["outputs"]
    assert Path(result["outputs"]["found_file"]).name == "output.txt"
    assert Path(result["outputs"]["found_file"]).exists()

def test_executor_post_exec_file_not_found(executor_tool: Tool, tmp_path: Path):
    """
    Tests that the Executor's post_exec hook raises an error if a file is not found.
    """
    # Modify the command so it *doesn't* create the file we're looking for
    executor_tool.command_template = "echo 'Just a message'"
    params = {"name": "World", "file": "non_existent_file.txt"}
    executor = Executor(tool=executor_tool, params=params)

    with pytest.raises(RuntimeError) as excinfo:
        executor.execute(work_dir=tmp_path)
    
    assert "Failed to resolve post_exec output" in str(excinfo.value)
    assert "No file found for pattern" in str(excinfo.value)

def test_executor_command_failure(tmp_path: Path):
    """
    Tests that the executor correctly captures the return code for a failing command.
    """
    tool_data = {"name": "fail-tool", "command_template": "exit 1"}
    tool = Tool(**tool_data)
    executor = Executor(tool=tool, params={})
    result = executor.execute(work_dir=tmp_path)
    assert result["returncode"] == 1