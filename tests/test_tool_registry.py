"""
Unit tests for the enhanced tool registry system.
"""

import pytest
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from dact.tool_registry import (
    ToolRegistry, RealToolAdapter, ToolType, ToolInfo, ToolDetails, 
    ToolAvailability, get_tool_registry, reset_tool_registry
)
from dact.models import Tool, ToolParameter, ToolValidation


class MockRealToolAdapter(RealToolAdapter):
    """Mock real tool adapter for testing."""
    
    def __init__(self, name: str, executable_name: str, available: bool = True, version: str = "1.0.0"):
        super().__init__(name, executable_name)
        self._mock_available = available
        self._mock_version = version
    
    @property
    def version_check_command(self) -> list:
        return [self.executable_name, "--version"]
    
    @property
    def minimum_version(self) -> str:
        return "1.0.0"
    
    def validate_parameters(self, parameters: dict) -> bool:
        return True
    
    def map_parameters(self, parameters: dict) -> list:
        return []
    
    def find_executable(self) -> str:
        return f"/usr/bin/{self.executable_name}" if self._mock_available else None


class TestRealToolAdapter:
    """Test cases for RealToolAdapter base class."""
    
    def test_adapter_initialization(self):
        """Test adapter initialization."""
        adapter = MockRealToolAdapter("test-tool", "test-executable")
        
        assert adapter.name == "test-tool"
        assert adapter.executable_name == "test-executable"
        assert adapter._cached_availability is None
    
    @patch('shutil.which')
    def test_find_executable_found(self, mock_which):
        """Test finding executable when it exists."""
        mock_which.return_value = "/usr/bin/test-tool"
        adapter = MockRealToolAdapter("test-tool", "test-tool")
        
        result = adapter.find_executable()
        
        assert result == "/usr/bin/test-tool"
        mock_which.assert_called_once_with("test-tool")
    
    @patch('shutil.which')
    def test_find_executable_not_found(self, mock_which):
        """Test finding executable when it doesn't exist."""
        mock_which.return_value = None
        adapter = MockRealToolAdapter("test-tool", "test-tool")
        
        result = adapter.find_executable()
        
        assert result is None
        mock_which.assert_called_once_with("test-tool")
    
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_check_availability_success(self, mock_which, mock_run):
        """Test successful availability check."""
        mock_which.return_value = "/usr/bin/test-tool"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="test-tool version 1.2.0\n"
        )
        
        adapter = MockRealToolAdapter("test-tool", "test-tool")
        result = adapter.check_availability()
        
        assert result.name == "test-tool"
        assert result.available is True
        assert result.version == "1.2.0"
        assert result.path == "/usr/bin/test-tool"
        assert result.error_message is None
    
    @patch('shutil.which')
    def test_check_availability_executable_not_found(self, mock_which):
        """Test availability check when executable is not found."""
        mock_which.return_value = None
        
        adapter = MockRealToolAdapter("test-tool", "test-tool")
        result = adapter.check_availability()
        
        assert result.name == "test-tool"
        assert result.available is False
        assert result.version is None
        assert result.path is None
        assert "not found in PATH" in result.error_message
    
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_check_availability_version_check_fails(self, mock_which, mock_run):
        """Test availability check when version check fails."""
        mock_which.return_value = "/usr/bin/test-tool"
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Command not found"
        )
        
        adapter = MockRealToolAdapter("test-tool", "test-tool")
        result = adapter.check_availability()
        
        assert result.name == "test-tool"
        assert result.available is False
        assert result.path == "/usr/bin/test-tool"
        assert "Version check failed" in result.error_message
    
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_check_availability_timeout(self, mock_which, mock_run):
        """Test availability check when version check times out."""
        mock_which.return_value = "/usr/bin/test-tool"
        mock_run.side_effect = subprocess.TimeoutExpired("test-tool", 10)
        
        adapter = MockRealToolAdapter("test-tool", "test-tool")
        result = adapter.check_availability()
        
        assert result.name == "test-tool"
        assert result.available is False
        assert result.path == "/usr/bin/test-tool"
        assert "timed out" in result.error_message
    
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_check_availability_caching(self, mock_which, mock_run):
        """Test that availability results are cached."""
        mock_which.return_value = "/usr/bin/test-tool"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="test-tool version 1.2.0\n"
        )
        
        adapter = MockRealToolAdapter("test-tool", "test-tool")
        
        # First call
        result1 = adapter.check_availability()
        # Second call should use cache
        result2 = adapter.check_availability()
        
        assert result1 == result2
        # subprocess.run should only be called once due to caching
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_check_availability_force_refresh(self, mock_which, mock_run):
        """Test forcing refresh bypasses cache."""
        mock_which.return_value = "/usr/bin/test-tool"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="test-tool version 1.2.0\n"
        )
        
        adapter = MockRealToolAdapter("test-tool", "test-tool")
        
        # First call
        result1 = adapter.check_availability()
        # Second call with force_refresh should bypass cache
        result2 = adapter.check_availability(force_refresh=True)
        
        assert result1.available == result2.available
        # subprocess.run should be called twice
        assert mock_run.call_count == 2


class TestToolRegistry:
    """Test cases for ToolRegistry class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.registry = ToolRegistry()
        
        # Create test tool
        self.test_tool = Tool(
            name="test-tool",
            type="shell",
            description="Test tool for unit tests",
            parameters={
                "input": ToolParameter(type="str", required=True, help="Input parameter"),
                "output": ToolParameter(type="str", default="output.txt", help="Output parameter")
            },
            command_template="echo '{{ input }}' > {{ output }}",
            validation=ToolValidation(exit_code=0)
        )
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = ToolRegistry()
        
        assert len(registry._tools) == 0
        assert len(registry._real_tool_adapters) == 0
        assert len(registry._tool_availability_cache) == 0
    
    def test_register_tool_success(self):
        """Test successful tool registration."""
        self.registry.register_tool(self.test_tool)
        
        assert "test-tool" in self.registry._tools
        assert self.registry._tools["test-tool"] == self.test_tool
    
    def test_register_tool_duplicate_name(self):
        """Test registering tool with duplicate name raises error."""
        self.registry.register_tool(self.test_tool)
        
        duplicate_tool = Tool(
            name="test-tool",
            type="shell",
            command_template="different command"
        )
        
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register_tool(duplicate_tool)
    
    def test_register_real_tool_adapter(self):
        """Test registering real tool adapter."""
        adapter = MockRealToolAdapter("real-tool", "real-executable")
        self.registry.register_real_tool_adapter(adapter)
        
        assert "real-tool" in self.registry._real_tool_adapters
        assert self.registry._real_tool_adapters["real-tool"] == adapter
    
    def test_get_tool_exists(self):
        """Test getting existing tool."""
        self.registry.register_tool(self.test_tool)
        
        result = self.registry.get_tool("test-tool")
        
        assert result == self.test_tool
    
    def test_get_tool_not_exists(self):
        """Test getting non-existent tool."""
        result = self.registry.get_tool("non-existent")
        
        assert result is None
    
    def test_get_real_tool_adapter_exists(self):
        """Test getting existing real tool adapter."""
        adapter = MockRealToolAdapter("real-tool", "real-executable")
        self.registry.register_real_tool_adapter(adapter)
        
        result = self.registry.get_real_tool_adapter("real-tool")
        
        assert result == adapter
    
    def test_get_real_tool_adapter_not_exists(self):
        """Test getting non-existent real tool adapter."""
        result = self.registry.get_real_tool_adapter("non-existent")
        
        assert result is None
    
    def test_list_tools_empty(self):
        """Test listing tools when registry is empty."""
        result = self.registry.list_tools()
        
        assert result == []
    
    def test_list_tools_with_yaml_tool(self):
        """Test listing tools with YAML-defined tool."""
        self.registry.register_tool(self.test_tool)
        
        result = self.registry.list_tools()
        
        assert len(result) == 1
        tool_info = result[0]
        assert tool_info.name == "test-tool"
        assert tool_info.type == ToolType.SHELL
        assert tool_info.description == "Test tool for unit tests"
        assert tool_info.available is True  # YAML tools are assumed available
    
    def test_list_tools_with_real_adapter(self):
        """Test listing tools with real tool adapter."""
        adapter = MockRealToolAdapter("real-tool", "real-executable", available=True, version="1.0.0")
        self.registry.register_real_tool_adapter(adapter)
        
        with patch.object(adapter, 'check_availability') as mock_check:
            mock_check.return_value = ToolAvailability(
                name="real-tool",
                available=True,
                version="1.0.0",
                path="/usr/bin/real-executable"
            )
            
            result = self.registry.list_tools()
        
        assert len(result) == 1
        tool_info = result[0]
        assert tool_info.name == "real-tool"
        assert tool_info.type == ToolType.REAL
        assert tool_info.available is True
        assert tool_info.version == "1.0.0"
    
    def test_list_tools_sorted_by_name(self):
        """Test that tools are sorted by name."""
        tool_z = Tool(name="z-tool", type="shell", command_template="echo z")
        tool_a = Tool(name="a-tool", type="shell", command_template="echo a")
        
        self.registry.register_tool(tool_z)
        self.registry.register_tool(tool_a)
        
        result = self.registry.list_tools()
        
        assert len(result) == 2
        assert result[0].name == "a-tool"
        assert result[1].name == "z-tool"
    
    def test_get_tool_details_yaml_tool(self):
        """Test getting details for YAML-defined tool."""
        self.registry.register_tool(self.test_tool)
        
        result = self.registry.get_tool_details("test-tool")
        
        assert result is not None
        assert result.name == "test-tool"
        assert result.type == ToolType.SHELL
        assert result.description == "Test tool for unit tests"
        assert result.available is True
        assert len(result.parameters) == 2
        assert "input" in result.parameters
        assert "output" in result.parameters
        assert result.validation_rules is not None
    
    def test_get_tool_details_real_adapter(self):
        """Test getting details for real tool adapter."""
        adapter = MockRealToolAdapter("real-tool", "real-executable")
        self.registry.register_real_tool_adapter(adapter)
        
        with patch.object(adapter, 'check_availability') as mock_check:
            mock_check.return_value = ToolAvailability(
                name="real-tool",
                available=True,
                version="1.0.0",
                path="/usr/bin/real-executable"
            )
            
            result = self.registry.get_tool_details("real-tool")
        
        assert result is not None
        assert result.name == "real-tool"
        assert result.type == ToolType.REAL
        assert result.available is True
        assert result.version == "1.0.0"
        assert result.executable_path == "/usr/bin/real-executable"
    
    def test_get_tool_details_not_found(self):
        """Test getting details for non-existent tool."""
        result = self.registry.get_tool_details("non-existent")
        
        assert result is None
    
    def test_validate_tool_availability_yaml_tool(self):
        """Test validating availability of YAML tool."""
        self.registry.register_tool(self.test_tool)
        
        result = self.registry.validate_tool_availability("test-tool")
        
        assert result.name == "test-tool"
        assert result.available is True
        assert result.version is None
        assert result.path is None
        assert result.error_message is None
    
    def test_validate_tool_availability_real_adapter(self):
        """Test validating availability of real tool adapter."""
        adapter = MockRealToolAdapter("real-tool", "real-executable")
        self.registry.register_real_tool_adapter(adapter)
        
        with patch.object(adapter, 'check_availability') as mock_check:
            mock_availability = ToolAvailability(
                name="real-tool",
                available=True,
                version="1.0.0",
                path="/usr/bin/real-executable"
            )
            mock_check.return_value = mock_availability
            
            result = self.registry.validate_tool_availability("real-tool")
        
        assert result == mock_availability
    
    def test_validate_tool_availability_not_found(self):
        """Test validating availability of non-existent tool."""
        result = self.registry.validate_tool_availability("non-existent")
        
        assert result.name == "non-existent"
        assert result.available is False
        assert "not registered" in result.error_message
    
    def test_validate_tool_availability_caching(self):
        """Test that availability results are cached."""
        adapter = MockRealToolAdapter("real-tool", "real-executable")
        self.registry.register_real_tool_adapter(adapter)
        
        with patch.object(adapter, 'check_availability') as mock_check:
            mock_availability = ToolAvailability(
                name="real-tool",
                available=True,
                version="1.0.0"
            )
            mock_check.return_value = mock_availability
            
            # First call
            result1 = self.registry.validate_tool_availability("real-tool")
            # Second call should use cache
            result2 = self.registry.validate_tool_availability("real-tool")
        
        assert result1 == result2
        # check_availability should only be called once due to caching
        mock_check.assert_called_once()
    
    def test_clear_availability_cache(self):
        """Test clearing availability cache."""
        adapter = MockRealToolAdapter("real-tool", "real-executable")
        self.registry.register_real_tool_adapter(adapter)
        
        # Populate cache
        self.registry.validate_tool_availability("real-tool")
        assert len(self.registry._tool_availability_cache) > 0
        
        # Clear cache
        self.registry.clear_availability_cache()
        assert len(self.registry._tool_availability_cache) == 0
        assert adapter._cached_availability is None
    
    def test_get_available_tools(self):
        """Test getting list of available tools."""
        # Add available tool
        self.registry.register_tool(self.test_tool)
        
        # Add unavailable adapter
        adapter = MockRealToolAdapter("unavailable-tool", "unavailable-executable", available=False)
        self.registry.register_real_tool_adapter(adapter)
        
        with patch.object(adapter, 'check_availability') as mock_check:
            mock_check.return_value = ToolAvailability(
                name="unavailable-tool",
                available=False,
                error_message="Not found"
            )
            
            result = self.registry.get_available_tools()
        
        assert "test-tool" in result
        assert "unavailable-tool" not in result
    
    def test_get_unavailable_tools(self):
        """Test getting list of unavailable tools."""
        # Add available tool
        self.registry.register_tool(self.test_tool)
        
        # Add unavailable adapter
        adapter = MockRealToolAdapter("unavailable-tool", "unavailable-executable", available=False)
        self.registry.register_real_tool_adapter(adapter)
        
        with patch.object(adapter, 'check_availability') as mock_check:
            mock_check.return_value = ToolAvailability(
                name="unavailable-tool",
                available=False,
                error_message="Not found"
            )
            
            result = self.registry.get_unavailable_tools()
        
        assert "test-tool" not in result
        assert "unavailable-tool" in result


class TestGlobalRegistry:
    """Test cases for global registry functions."""
    
    def setup_method(self):
        """Reset global registry before each test."""
        reset_tool_registry()
    
    def teardown_method(self):
        """Reset global registry after each test."""
        reset_tool_registry()
    
    def test_get_tool_registry_singleton(self):
        """Test that get_tool_registry returns singleton instance."""
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()
        
        assert registry1 is registry2
        assert isinstance(registry1, ToolRegistry)
    
    def test_reset_tool_registry(self):
        """Test resetting global registry."""
        registry1 = get_tool_registry()
        reset_tool_registry()
        registry2 = get_tool_registry()
        
        assert registry1 is not registry2
        assert isinstance(registry2, ToolRegistry)