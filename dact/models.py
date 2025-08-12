from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ToolParameter(BaseModel):
    """A parameter for a tool."""
    type: str = "str"
    required: bool = False
    default: Any = None
    help: Optional[str] = None

class ToolOutput(BaseModel):
    """An output variable from a tool's execution."""
    # This will be implemented later, for now, it's a placeholder
    pass

class PostExec(BaseModel):
    """Defines operations to run after a tool command finishes."""
    outputs: Dict[str, str] = Field(default_factory=dict)

class ToolValidation(BaseModel):
    """Tool execution result validation rules."""
    exit_code: Optional[int] = 0
    stdout_contains: Optional[List[str]] = None
    stderr_not_contains: Optional[List[str]] = None
    output_files_exist: Optional[List[str]] = None

class Tool(BaseModel):
    """A tool definition."""
    name: str
    type: str = "shell"
    description: Optional[str] = None
    parameters: Dict[str, ToolParameter] = Field(default_factory=dict)
    command_template: str
    success_pattern: Optional[str] = None
    failure_pattern: Optional[str] = None
    timeout: Optional[int] = None
    retry_count: int = 0
    post_exec: Optional[PostExec] = None
    validation: Optional[ToolValidation] = None


class Step(BaseModel):
    """A step in a scenario."""
    name: str
    tool: str
    description: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    depends_on: Optional[List[str]] = None  # Explicit dependencies
    condition: Optional[str] = None         # Conditional execution
    retry_on_failure: bool = False          # Retry on failure
    continue_on_failure: bool = False       # Continue on failure
    timeout: Optional[int] = None           # Step timeout

class Scenario(BaseModel):
    """A scenario definition."""
    name: str
    description: Optional[str] = None
    version: str = "1.0"
    default_params: Dict[str, Any] = Field(default_factory=dict)
    environment: Dict[str, str] = Field(default_factory=dict)  # Environment variables
    steps: List[Step]
    cleanup_steps: Optional[List[Step]] = None  # Cleanup steps
    validation: Optional[Dict[str, Any]] = None  # Scenario-level validation

class CaseValidation(BaseModel):
    """A validation check for a case."""
    type: str  # "exit_code", "stdout_contains", "stderr_not_contains", "file_exists", "file_not_exists", 
              # "file_size", "file_content", "output_equals", "output_contains", "output_matches", 
              # "performance", "json_schema", "xml_schema", "custom"
    target: Optional[str] = None  # Target file, output variable, or step name
    expected: Any = None  # Expected value
    tolerance: Optional[float] = None  # For performance/numeric comparisons
    custom_validator: Optional[str] = None  # Custom validation function name
    pattern: Optional[str] = None  # Regex pattern for string matching
    description: Optional[str] = None  # Human-readable description of the validation
    validation_schema: Optional[Dict[str, Any]] = None  # JSON/XML schema for validation
    min_value: Optional[float] = None  # Minimum value for numeric comparisons
    max_value: Optional[float] = None  # Maximum value for numeric comparisons
    encoding: Optional[str] = "utf-8"  # File encoding for content validation

class Case(BaseModel):
    """A test case definition."""
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)  # Tags for test categorization
    scenario: Optional[str] = None
    tool: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    data_source: Optional[str] = None  # Path to data file for data-driven testing
    validation: List[CaseValidation] = Field(default_factory=list)
    setup: Optional[Dict[str, Any]] = None     # Pre-execution setup
    teardown: Optional[Dict[str, Any]] = None  # Post-execution cleanup
    timeout: Optional[int] = None  # Case-level timeout
    retry_count: int = 0  # Number of retries on failure

class DataDrivenCase(BaseModel):
    """A data-driven test case template."""
    template: Case
    data_source: str  # Path to CSV, JSON, or YAML file containing test data
    parameter_mapping: Dict[str, str] = Field(default_factory=dict)  # Maps data columns to case parameters
    data_filter: Optional[Dict[str, Any]] = None  # Filter criteria for data rows
    data_transform: Optional[Dict[str, str]] = None  # Data transformation expressions
    name_template: Optional[str] = None  # Template for generating test case names
    
class CaseFile(BaseModel):
    """A file containing one or more test cases."""
    common_params: Dict[str, Any] = Field(default_factory=dict)
    cases: List[Case]
    data_driven_cases: List[DataDrivenCase] = Field(default_factory=list)  # Data-driven test cases
