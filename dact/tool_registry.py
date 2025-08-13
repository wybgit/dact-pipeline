"""
Enhanced tool registry system for DACT framework.

This module provides a centralized registry for tools with support for:
- Tool registration and discovery
- Real tool integration through adapters
- Tool availability validation and version checking
- Enhanced error handling and reporting
"""

import subprocess
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from dact.models import Tool


class ToolType(Enum):
    """Types of tools supported by the registry."""
    SHELL = "shell"
    REAL = "real"
    MOCK = "mock"


@dataclass
class ToolInfo:
    """Brief information about a tool for listing purposes."""
    name: str
    type: ToolType
    description: Optional[str]
    available: bool
    version: Optional[str] = None


@dataclass
class ToolDetails:
    """Detailed information about a tool."""
    name: str
    type: ToolType
    description: Optional[str]
    available: bool
    version: Optional[str]
    executable_path: Optional[str]
    parameters: Dict[str, Any]
    validation_rules: Optional[Dict[str, Any]]
    error_message: Optional[str] = None


@dataclass
class ToolAvailability:
    """Tool availability status information."""
    name: str
    available: bool
    version: Optional[str] = None
    path: Optional[str] = None
    error_message: Optional[str] = None


class RealToolAdapter(ABC):
    """
    Base class for real tool integration adapters.
    
    This class provides the interface for integrating real external tools
    into the DACT framework, with support for availability checking,
    version validation, and parameter mapping.
    """
    
    def __init__(self, name: str, executable_name: str):
        self.name = name
        self.executable_name = executable_name
        self._cached_availability: Optional[ToolAvailability] = None
    
    @property
    @abstractmethod
    def version_check_command(self) -> List[str]:
        """Command to check tool version."""
        pass
    
    @property
    @abstractmethod
    def minimum_version(self) -> Optional[str]:
        """Minimum required version for this tool."""
        pass
    
    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate tool-specific parameters."""
        pass
    
    @abstractmethod
    def map_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Map YAML parameters to command-line arguments."""
        pass
    
    def find_executable(self) -> Optional[str]:
        """Find the executable path for this tool."""
        return shutil.which(self.executable_name)
    
    def check_availability(self, force_refresh: bool = False) -> ToolAvailability:
        """
        Check if the tool is available and get version information.
        
        Args:
            force_refresh: If True, bypass cache and check again
            
        Returns:
            ToolAvailability object with status information
        """
        if self._cached_availability and not force_refresh:
            return self._cached_availability
        
        executable_path = self.find_executable()
        if not executable_path:
            self._cached_availability = ToolAvailability(
                name=self.name,
                available=False,
                error_message=f"Executable '{self.executable_name}' not found in PATH"
            )
            return self._cached_availability
        
        try:
            # Check version
            result = subprocess.run(
                self.version_check_command,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = self._extract_version(result.stdout)
                if self._is_version_compatible(version):
                    self._cached_availability = ToolAvailability(
                        name=self.name,
                        available=True,
                        version=version,
                        path=executable_path
                    )
                else:
                    self._cached_availability = ToolAvailability(
                        name=self.name,
                        available=False,
                        version=version,
                        path=executable_path,
                        error_message=f"Version {version} is not compatible. Minimum required: {self.minimum_version}"
                    )
            else:
                self._cached_availability = ToolAvailability(
                    name=self.name,
                    available=False,
                    path=executable_path,
                    error_message=f"Version check failed: {result.stderr}"
                )
                
        except subprocess.TimeoutExpired:
            self._cached_availability = ToolAvailability(
                name=self.name,
                available=False,
                path=executable_path,
                error_message="Version check timed out"
            )
        except Exception as e:
            self._cached_availability = ToolAvailability(
                name=self.name,
                available=False,
                path=executable_path,
                error_message=f"Version check failed: {str(e)}"
            )
        
        return self._cached_availability
    
    def _extract_version(self, version_output: str) -> Optional[str]:
        """Extract version string from command output."""
        # Default implementation - can be overridden by subclasses
        lines = version_output.strip().split('\n')
        for line in lines:
            if 'version' in line.lower():
                # Try to extract version number
                import re
                version_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', line)
                if version_match:
                    return version_match.group(1)
        return None
    
    def _is_version_compatible(self, version: Optional[str]) -> bool:
        """Check if the detected version is compatible."""
        if not version or not self.minimum_version:
            return True
        
        try:
            from packaging import version as pkg_version
            return pkg_version.parse(version) >= pkg_version.parse(self.minimum_version)
        except ImportError:
            # Fallback to simple string comparison if packaging is not available
            return version >= self.minimum_version


class ToolRegistry:
    """
    Central registry for managing tools in the DACT framework.
    
    Provides capabilities for:
    - Tool registration and discovery
    - Tool availability validation
    - Tool information retrieval
    - Integration with both YAML-defined and real tools
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._real_tool_adapters: Dict[str, RealToolAdapter] = {}
        self._tool_availability_cache: Dict[str, ToolAvailability] = {}
    
    def register_tool(self, tool: Tool) -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool: Tool object to register
            
        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        
        self._tools[tool.name] = tool
        # Clear availability cache for this tool
        if tool.name in self._tool_availability_cache:
            del self._tool_availability_cache[tool.name]
    
    def register_real_tool_adapter(self, adapter: RealToolAdapter) -> None:
        """
        Register a real tool adapter.
        
        Args:
            adapter: RealToolAdapter instance to register
        """
        self._real_tool_adapters[adapter.name] = adapter
        # Clear availability cache for this tool
        if adapter.name in self._tool_availability_cache:
            del self._tool_availability_cache[adapter.name]
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name.
        
        Args:
            name: Name of the tool to retrieve
            
        Returns:
            Tool object if found, None otherwise
        """
        return self._tools.get(name)
    
    def get_real_tool_adapter(self, name: str) -> Optional[RealToolAdapter]:
        """
        Get a real tool adapter by name.
        
        Args:
            name: Name of the adapter to retrieve
            
        Returns:
            RealToolAdapter instance if found, None otherwise
        """
        return self._real_tool_adapters.get(name)
    
    def list_tools(self) -> List[ToolInfo]:
        """
        List all registered tools with brief information.
        
        Returns:
            List of ToolInfo objects
        """
        tool_infos = []
        
        # Add YAML-defined tools
        for tool in self._tools.values():
            availability = self.validate_tool_availability(tool.name)
            tool_infos.append(ToolInfo(
                name=tool.name,
                type=ToolType(tool.type) if tool.type in [t.value for t in ToolType] else ToolType.SHELL,
                description=tool.description,
                available=availability.available,
                version=availability.version
            ))
        
        # Add real tool adapters that aren't already in YAML tools
        for adapter in self._real_tool_adapters.values():
            if adapter.name not in self._tools:
                availability = adapter.check_availability()
                tool_infos.append(ToolInfo(
                    name=adapter.name,
                    type=ToolType.REAL,
                    description=f"Real tool adapter for {adapter.name}",
                    available=availability.available,
                    version=availability.version
                ))
        
        return sorted(tool_infos, key=lambda x: x.name)
    
    def get_tool_details(self, name: str) -> Optional[ToolDetails]:
        """
        Get detailed information about a specific tool.
        
        Args:
            name: Name of the tool
            
        Returns:
            ToolDetails object if tool exists, None otherwise
        """
        # Check YAML-defined tools first
        tool = self._tools.get(name)
        if tool:
            availability = self.validate_tool_availability(name)
            return ToolDetails(
                name=tool.name,
                type=ToolType(tool.type) if tool.type in [t.value for t in ToolType] else ToolType.SHELL,
                description=tool.description,
                available=availability.available,
                version=availability.version,
                executable_path=availability.path,
                parameters={param_name: param.dict() for param_name, param in tool.parameters.items()},
                validation_rules=tool.validation.dict() if tool.validation else None,
                error_message=availability.error_message
            )
        
        # Check real tool adapters
        adapter = self._real_tool_adapters.get(name)
        if adapter:
            availability = adapter.check_availability()
            return ToolDetails(
                name=adapter.name,
                type=ToolType.REAL,
                description=f"Real tool adapter for {adapter.name}",
                available=availability.available,
                version=availability.version,
                executable_path=availability.path,
                parameters={},  # Real tool adapters define parameters differently
                validation_rules=None,
                error_message=availability.error_message
            )
        
        return None
    
    def validate_tool_availability(self, name: str, force_refresh: bool = False) -> ToolAvailability:
        """
        Validate if a tool is available for execution.
        
        Args:
            name: Name of the tool to validate
            force_refresh: If True, bypass cache and check again
            
        Returns:
            ToolAvailability object with validation results
        """
        if not force_refresh and name in self._tool_availability_cache:
            return self._tool_availability_cache[name]
        
        # Check real tool adapters first
        adapter = self._real_tool_adapters.get(name)
        if adapter:
            availability = adapter.check_availability(force_refresh)
            self._tool_availability_cache[name] = availability
            return availability
        
        # Check YAML-defined tools
        tool = self._tools.get(name)
        if tool:
            # For YAML-defined tools, we assume they're available unless they reference real tools
            availability = ToolAvailability(
                name=name,
                available=True,
                version=None,
                path=None
            )
            self._tool_availability_cache[name] = availability
            return availability
        
        # Tool not found
        availability = ToolAvailability(
            name=name,
            available=False,
            error_message=f"Tool '{name}' is not registered"
        )
        self._tool_availability_cache[name] = availability
        return availability
    
    def clear_availability_cache(self) -> None:
        """Clear the tool availability cache."""
        self._tool_availability_cache.clear()
        # Also clear adapter caches
        for adapter in self._real_tool_adapters.values():
            adapter._cached_availability = None
    
    def get_available_tools(self) -> List[str]:
        """
        Get list of available tool names.
        
        Returns:
            List of tool names that are currently available
        """
        available_tools = []
        for tool_info in self.list_tools():
            if tool_info.available:
                available_tools.append(tool_info.name)
        return available_tools
    
    def get_unavailable_tools(self) -> List[str]:
        """
        Get list of unavailable tool names.
        
        Returns:
            List of tool names that are currently unavailable
        """
        unavailable_tools = []
        for tool_info in self.list_tools():
            if not tool_info.available:
                unavailable_tools.append(tool_info.name)
        return unavailable_tools


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_tool_registry() -> None:
    """Reset the global tool registry (mainly for testing)."""
    global _global_registry
    _global_registry = None