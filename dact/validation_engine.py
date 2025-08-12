"""
Validation engine for test case validation.
"""
import os
import re
import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dact.models import CaseValidation
from dact.logger import log


class ValidationResult:
    """Result of a validation check."""
    
    def __init__(self, is_valid: bool, message: str, details: Optional[Dict[str, Any]] = None):
        self.is_valid = is_valid
        self.message = message
        self.details = details or {}


class ValidationEngine:
    """Engine for executing various types of validations."""
    
    def __init__(self):
        self.custom_validators = {}
    
    def register_custom_validator(self, name: str, validator_func):
        """Register a custom validation function."""
        self.custom_validators[name] = validator_func
    
    def validate_case(self, validations: List[CaseValidation], 
                     execution_result: Dict[str, Any], 
                     work_dir: Path) -> List[ValidationResult]:
        """Execute all validations for a test case."""
        results = []
        
        for validation in validations:
            try:
                result = self._execute_validation(validation, execution_result, work_dir)
                results.append(result)
                
                if validation.description:
                    log.info(f"  Validation '{validation.description}': {'✓' if result.is_valid else '✗'}")
                else:
                    log.info(f"  Validation {validation.type}: {'✓' if result.is_valid else '✗'}")
                    
                if not result.is_valid:
                    log.error(f"    {result.message}")
                    
            except Exception as e:
                error_result = ValidationResult(
                    is_valid=False,
                    message=f"Validation execution failed: {str(e)}",
                    details={"validation": validation.dict(), "error": str(e)}
                )
                results.append(error_result)
                log.error(f"  Validation {validation.type} failed with error: {e}")
        
        return results
    
    def _execute_validation(self, validation: CaseValidation, 
                          execution_result: Dict[str, Any], 
                          work_dir: Path) -> ValidationResult:
        """Execute a single validation."""
        
        if validation.type == "exit_code":
            return self._validate_exit_code(validation, execution_result)
        
        elif validation.type == "stdout_contains":
            return self._validate_stdout_contains(validation, execution_result)
        
        elif validation.type == "stderr_not_contains":
            return self._validate_stderr_not_contains(validation, execution_result)
        
        elif validation.type == "file_exists":
            return self._validate_file_exists(validation, work_dir)
        
        elif validation.type == "file_not_exists":
            return self._validate_file_not_exists(validation, work_dir)
        
        elif validation.type == "file_size":
            return self._validate_file_size(validation, work_dir)
        
        elif validation.type == "output_equals":
            return self._validate_output_equals(validation, execution_result)
        
        elif validation.type == "output_contains":
            return self._validate_output_contains(validation, execution_result)
        
        elif validation.type == "output_matches":
            return self._validate_output_matches(validation, execution_result)
        
        elif validation.type == "file_content":
            return self._validate_file_content(validation, work_dir)
        
        elif validation.type == "performance":
            return self._validate_performance(validation, execution_result)
        
        elif validation.type == "json_schema":
            return self._validate_json_schema(validation, execution_result, work_dir)
        
        elif validation.type == "xml_schema":
            return self._validate_xml_schema(validation, execution_result, work_dir)
        
        elif validation.type == "numeric_range":
            return self._validate_numeric_range(validation, execution_result)
        
        elif validation.type == "custom":
            return self._validate_custom(validation, execution_result, work_dir)
        
        else:
            return ValidationResult(
                is_valid=False,
                message=f"Unknown validation type: {validation.type}"
            )
    
    def _validate_exit_code(self, validation: CaseValidation, 
                           execution_result: Dict[str, Any]) -> ValidationResult:
        """Validate the exit code of the execution."""
        expected_code = validation.expected if validation.expected is not None else 0
        actual_code = execution_result.get("returncode", -1)
        
        is_valid = actual_code == expected_code
        message = f"Expected exit code {expected_code}, got {actual_code}"
        
        return ValidationResult(is_valid, message, {
            "expected": expected_code,
            "actual": actual_code
        })
    
    def _validate_stdout_contains(self, validation: CaseValidation, 
                                 execution_result: Dict[str, Any]) -> ValidationResult:
        """Validate that stdout contains expected text."""
        stdout = execution_result.get("stdout", "")
        expected_text = validation.expected
        
        if expected_text is None:
            return ValidationResult(False, "Expected text not specified for stdout_contains validation")
        
        is_valid = expected_text in stdout
        message = f"Expected stdout to contain '{expected_text}'"
        if not is_valid:
            message += f", but got: {stdout[:200]}..."
        
        return ValidationResult(is_valid, message, {
            "expected": expected_text,
            "actual": stdout
        })
    
    def _validate_stderr_not_contains(self, validation: CaseValidation, 
                                     execution_result: Dict[str, Any]) -> ValidationResult:
        """Validate that stderr does not contain specified text."""
        stderr = execution_result.get("stderr", "")
        forbidden_text = validation.expected
        
        if forbidden_text is None:
            return ValidationResult(False, "Forbidden text not specified for stderr_not_contains validation")
        
        is_valid = forbidden_text not in stderr
        message = f"Expected stderr to not contain '{forbidden_text}'"
        if not is_valid:
            message += f", but found it in: {stderr[:200]}..."
        
        return ValidationResult(is_valid, message, {
            "forbidden": forbidden_text,
            "actual": stderr
        })
    
    def _validate_file_exists(self, validation: CaseValidation, work_dir: Path) -> ValidationResult:
        """Validate that a file exists."""
        if not validation.target:
            return ValidationResult(False, "File path not specified for file_exists validation")
        
        file_path = work_dir / validation.target
        is_valid = file_path.exists()
        message = f"Expected file '{validation.target}' to exist"
        if not is_valid:
            message += f" in {work_dir}"
        
        return ValidationResult(is_valid, message, {
            "file_path": str(file_path),
            "exists": is_valid
        })
    
    def _validate_file_not_exists(self, validation: CaseValidation, work_dir: Path) -> ValidationResult:
        """Validate that a file does not exist."""
        if not validation.target:
            return ValidationResult(False, "File path not specified for file_not_exists validation")
        
        file_path = work_dir / validation.target
        is_valid = not file_path.exists()
        message = f"Expected file '{validation.target}' to not exist"
        if not is_valid:
            message += f", but it exists in {work_dir}"
        
        return ValidationResult(is_valid, message, {
            "file_path": str(file_path),
            "exists": file_path.exists()
        })
    
    def _validate_file_size(self, validation: CaseValidation, work_dir: Path) -> ValidationResult:
        """Validate file size."""
        if not validation.target:
            return ValidationResult(False, "File path not specified for file_size validation")
        
        file_path = work_dir / validation.target
        if not file_path.exists():
            return ValidationResult(False, f"File '{validation.target}' does not exist")
        
        actual_size = file_path.stat().st_size
        expected_size = validation.expected
        tolerance = validation.tolerance or 0
        
        if expected_size is None:
            return ValidationResult(False, "Expected file size not specified")
        
        is_valid = abs(actual_size - expected_size) <= tolerance
        message = f"Expected file size {expected_size} ± {tolerance}, got {actual_size}"
        
        return ValidationResult(is_valid, message, {
            "expected": expected_size,
            "actual": actual_size,
            "tolerance": tolerance
        })
    
    def _validate_output_equals(self, validation: CaseValidation, 
                               execution_result: Dict[str, Any]) -> ValidationResult:
        """Validate that an output variable equals expected value."""
        if not validation.target:
            return ValidationResult(False, "Output variable name not specified for output_equals validation")
        
        outputs = execution_result.get("outputs", {})
        actual_value = outputs.get(validation.target)
        expected_value = validation.expected
        
        is_valid = actual_value == expected_value
        message = f"Expected output '{validation.target}' to equal '{expected_value}', got '{actual_value}'"
        
        return ValidationResult(is_valid, message, {
            "expected": expected_value,
            "actual": actual_value
        })
    
    def _validate_output_contains(self, validation: CaseValidation, 
                                 execution_result: Dict[str, Any]) -> ValidationResult:
        """Validate that an output variable contains expected text."""
        if not validation.target:
            return ValidationResult(False, "Output variable name not specified for output_contains validation")
        
        outputs = execution_result.get("outputs", {})
        actual_value = str(outputs.get(validation.target, ""))
        expected_text = validation.expected
        
        if expected_text is None:
            return ValidationResult(False, "Expected text not specified for output_contains validation")
        
        is_valid = expected_text in actual_value
        message = f"Expected output '{validation.target}' to contain '{expected_text}'"
        if not is_valid:
            message += f", got '{actual_value}'"
        
        return ValidationResult(is_valid, message, {
            "expected": expected_text,
            "actual": actual_value
        })
    
    def _validate_output_matches(self, validation: CaseValidation, 
                                execution_result: Dict[str, Any]) -> ValidationResult:
        """Validate that an output variable matches a regex pattern."""
        if not validation.target:
            return ValidationResult(False, "Output variable name not specified for output_matches validation")
        
        if not validation.pattern:
            return ValidationResult(False, "Regex pattern not specified for output_matches validation")
        
        outputs = execution_result.get("outputs", {})
        actual_value = str(outputs.get(validation.target, ""))
        
        try:
            is_valid = bool(re.search(validation.pattern, actual_value))
            message = f"Expected output '{validation.target}' to match pattern '{validation.pattern}'"
            if not is_valid:
                message += f", got '{actual_value}'"
            
            return ValidationResult(is_valid, message, {
                "pattern": validation.pattern,
                "actual": actual_value
            })
        except re.error as e:
            return ValidationResult(False, f"Invalid regex pattern '{validation.pattern}': {e}")
    
    def _validate_file_content(self, validation: CaseValidation, work_dir: Path) -> ValidationResult:
        """Validate file content against expected content or pattern."""
        if not validation.target:
            return ValidationResult(False, "File path not specified for file_content validation")
        
        file_path = work_dir / validation.target
        if not file_path.exists():
            return ValidationResult(False, f"File '{validation.target}' does not exist")
        
        try:
            encoding = validation.encoding or "utf-8"
            content = file_path.read_text(encoding=encoding)
            
            if validation.expected is not None:
                # Exact content match
                is_valid = content == validation.expected
                message = f"Expected file content to match exactly"
                if not is_valid:
                    message += f", got content with length {len(content)}"
            elif validation.pattern:
                # Pattern match
                is_valid = bool(re.search(validation.pattern, content))
                message = f"Expected file content to match pattern '{validation.pattern}'"
                if not is_valid:
                    message += f", content: {content[:100]}..."
            else:
                return ValidationResult(False, "Neither expected content nor pattern specified for file_content validation")
            
            return ValidationResult(is_valid, message, {
                "file_path": str(file_path),
                "content_length": len(content)
            })
            
        except UnicodeDecodeError as e:
            return ValidationResult(False, f"Failed to decode file '{validation.target}' with encoding '{encoding}': {e}")
        except Exception as e:
            return ValidationResult(False, f"Failed to read file '{validation.target}': {e}")
    
    def _validate_performance(self, validation: CaseValidation, 
                             execution_result: Dict[str, Any]) -> ValidationResult:
        """Validate performance metrics."""
        if not validation.target:
            return ValidationResult(False, "Performance metric name not specified")
        
        # Look for performance metrics in execution result
        metrics = execution_result.get("metrics", {})
        if validation.target not in metrics:
            return ValidationResult(False, f"Performance metric '{validation.target}' not found")
        
        actual_value = metrics[validation.target]
        
        # Validate against expected value with tolerance
        if validation.expected is not None:
            tolerance = validation.tolerance or 0
            is_valid = abs(actual_value - validation.expected) <= tolerance
            message = f"Expected {validation.target} to be {validation.expected} ± {tolerance}, got {actual_value}"
        # Validate against min/max range
        elif validation.min_value is not None or validation.max_value is not None:
            is_valid = True
            message_parts = []
            
            if validation.min_value is not None and actual_value < validation.min_value:
                is_valid = False
                message_parts.append(f"below minimum {validation.min_value}")
            
            if validation.max_value is not None and actual_value > validation.max_value:
                is_valid = False
                message_parts.append(f"above maximum {validation.max_value}")
            
            if is_valid:
                message = f"Performance metric {validation.target} = {actual_value} is within acceptable range"
            else:
                message = f"Performance metric {validation.target} = {actual_value} is {' and '.join(message_parts)}"
        else:
            return ValidationResult(False, "No performance criteria specified (expected, min_value, or max_value)")
        
        return ValidationResult(is_valid, message, {
            "metric": validation.target,
            "actual": actual_value,
            "expected": validation.expected,
            "tolerance": validation.tolerance
        })
    
    def _validate_json_schema(self, validation: CaseValidation, 
                             execution_result: Dict[str, Any], 
                             work_dir: Path) -> ValidationResult:
        """Validate JSON content against a schema."""
        try:
            import jsonschema
        except ImportError:
            return ValidationResult(False, "jsonschema library not available for JSON schema validation")
        
        if not validation.validation_schema:
            return ValidationResult(False, "JSON schema not specified")
        
        # Get JSON content to validate
        if validation.target:
            if validation.target.endswith('.json'):
                # Validate file content
                file_path = work_dir / validation.target
                if not file_path.exists():
                    return ValidationResult(False, f"JSON file '{validation.target}' does not exist")
                try:
                    with open(file_path, 'r') as f:
                        json_data = json.load(f)
                except json.JSONDecodeError as e:
                    return ValidationResult(False, f"Invalid JSON in file '{validation.target}': {e}")
            else:
                # Validate output variable
                outputs = execution_result.get("outputs", {})
                if validation.target not in outputs:
                    return ValidationResult(False, f"Output variable '{validation.target}' not found")
                json_data = outputs[validation.target]
                if isinstance(json_data, str):
                    try:
                        json_data = json.loads(json_data)
                    except json.JSONDecodeError as e:
                        return ValidationResult(False, f"Output '{validation.target}' is not valid JSON: {e}")
        else:
            return ValidationResult(False, "Target not specified for JSON schema validation")
        
        try:
            jsonschema.validate(json_data, validation.validation_schema)
            return ValidationResult(True, f"JSON data validates against schema")
        except jsonschema.ValidationError as e:
            return ValidationResult(False, f"JSON schema validation failed: {e.message}")
        except Exception as e:
            return ValidationResult(False, f"JSON schema validation error: {e}")
    
    def _validate_xml_schema(self, validation: CaseValidation, 
                            execution_result: Dict[str, Any], 
                            work_dir: Path) -> ValidationResult:
        """Validate XML content against a schema."""
        try:
            from lxml import etree
        except ImportError:
            return ValidationResult(False, "lxml library not available for XML schema validation")
        
        if not validation.validation_schema:
            return ValidationResult(False, "XML schema not specified")
        
        # Get XML content to validate
        if validation.target:
            if validation.target.endswith('.xml'):
                # Validate file content
                file_path = work_dir / validation.target
                if not file_path.exists():
                    return ValidationResult(False, f"XML file '{validation.target}' does not exist")
                try:
                    xml_doc = etree.parse(str(file_path))
                except etree.XMLSyntaxError as e:
                    return ValidationResult(False, f"Invalid XML in file '{validation.target}': {e}")
            else:
                # Validate output variable
                outputs = execution_result.get("outputs", {})
                if validation.target not in outputs:
                    return ValidationResult(False, f"Output variable '{validation.target}' not found")
                xml_content = outputs[validation.target]
                try:
                    xml_doc = etree.fromstring(xml_content)
                except etree.XMLSyntaxError as e:
                    return ValidationResult(False, f"Output '{validation.target}' is not valid XML: {e}")
        else:
            return ValidationResult(False, "Target not specified for XML schema validation")
        
        try:
            # Create schema from validation.validation_schema (should be XSD content)
            schema_doc = etree.fromstring(validation.validation_schema)
            schema = etree.XMLSchema(schema_doc)
            
            if schema.validate(xml_doc):
                return ValidationResult(True, "XML validates against schema")
            else:
                errors = [str(error) for error in schema.error_log]
                return ValidationResult(False, f"XML schema validation failed: {'; '.join(errors)}")
        except Exception as e:
            return ValidationResult(False, f"XML schema validation error: {e}")
    
    def _validate_numeric_range(self, validation: CaseValidation, 
                               execution_result: Dict[str, Any]) -> ValidationResult:
        """Validate that a numeric value is within specified range."""
        if not validation.target:
            return ValidationResult(False, "Target not specified for numeric_range validation")
        
        outputs = execution_result.get("outputs", {})
        if validation.target not in outputs:
            return ValidationResult(False, f"Output variable '{validation.target}' not found")
        
        try:
            actual_value = float(outputs[validation.target])
        except (ValueError, TypeError):
            return ValidationResult(False, f"Output '{validation.target}' is not a numeric value")
        
        is_valid = True
        message_parts = []
        
        if validation.min_value is not None and actual_value < validation.min_value:
            is_valid = False
            message_parts.append(f"below minimum {validation.min_value}")
        
        if validation.max_value is not None and actual_value > validation.max_value:
            is_valid = False
            message_parts.append(f"above maximum {validation.max_value}")
        
        if is_valid:
            message = f"Value {actual_value} is within acceptable range"
        else:
            message = f"Value {actual_value} is {' and '.join(message_parts)}"
        
        return ValidationResult(is_valid, message, {
            "actual": actual_value,
            "min_value": validation.min_value,
            "max_value": validation.max_value
        })
    
    def _validate_custom(self, validation: CaseValidation, 
                        execution_result: Dict[str, Any], 
                        work_dir: Path) -> ValidationResult:
        """Execute a custom validation function."""
        if not validation.custom_validator:
            return ValidationResult(False, "Custom validator function name not specified")
        
        validator_func = self.custom_validators.get(validation.custom_validator)
        if not validator_func:
            return ValidationResult(False, f"Custom validator '{validation.custom_validator}' not registered")
        
        try:
            result = validator_func(validation, execution_result, work_dir)
            if isinstance(result, ValidationResult):
                return result
            elif isinstance(result, bool):
                return ValidationResult(result, f"Custom validation '{validation.custom_validator}' result")
            else:
                return ValidationResult(False, f"Custom validator returned invalid result type: {type(result)}")
        except Exception as e:
            return ValidationResult(False, f"Custom validator '{validation.custom_validator}' failed: {e}")