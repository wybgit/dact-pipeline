"""
Data providers for data-driven testing.
"""
import csv
import json
import yaml
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from dact.logger import log


class DataProvider(ABC):
    """Abstract base class for data providers."""
    
    @abstractmethod
    def load_data(self, source: str) -> List[Dict[str, Any]]:
        """Load test data from the specified source."""
        pass
    
    @abstractmethod
    def validate_data_schema(self, data: List[Dict], schema: Dict) -> bool:
        """Validate that the data matches the expected schema."""
        pass


class CSVDataProvider(DataProvider):
    """Data provider for CSV files."""
    
    def load_data(self, source: str) -> List[Dict[str, Any]]:
        """Load data from a CSV file."""
        data = []
        source_path = Path(source)
        
        if not source_path.exists():
            raise FileNotFoundError(f"CSV file not found: {source}")
        
        try:
            with open(source_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Convert string values to appropriate types
                    converted_row = {}
                    for key, value in row.items():
                        converted_row[key] = self._convert_value(value)
                    data.append(converted_row)
            
            log.info(f"Loaded {len(data)} rows from CSV file: {source}")
            return data
            
        except Exception as e:
            raise ValueError(f"Failed to load CSV file {source}: {e}")
    
    def validate_data_schema(self, data: List[Dict], schema: Dict) -> bool:
        """Validate CSV data against a schema."""
        if not data:
            return True
        
        required_columns = schema.get('required_columns', [])
        optional_columns = schema.get('optional_columns', [])
        all_allowed_columns = set(required_columns + optional_columns)
        
        # Check first row for column validation
        first_row = data[0]
        actual_columns = set(first_row.keys())
        
        # Check required columns
        missing_required = set(required_columns) - actual_columns
        if missing_required:
            log.error(f"Missing required columns: {missing_required}")
            return False
        
        # Check for unexpected columns
        unexpected_columns = actual_columns - all_allowed_columns
        if unexpected_columns:
            log.warning(f"Unexpected columns found: {unexpected_columns}")
        
        return True
    
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate Python type."""
        if value == '':
            return None
        
        # Try to convert to int
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try to convert to float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try to convert to boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Return as string
        return value


class JSONDataProvider(DataProvider):
    """Data provider for JSON files."""
    
    def load_data(self, source: str) -> List[Dict[str, Any]]:
        """Load data from a JSON file."""
        source_path = Path(source)
        
        if not source_path.exists():
            raise FileNotFoundError(f"JSON file not found: {source}")
        
        try:
            with open(source_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
            
            # Ensure data is a list of dictionaries
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                raise ValueError("JSON data must be a list of objects or a single object")
            
            # Validate that all items are dictionaries
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    raise ValueError(f"Item {i} in JSON data is not an object")
            
            log.info(f"Loaded {len(data)} items from JSON file: {source}")
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file {source}: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load JSON file {source}: {e}")
    
    def validate_data_schema(self, data: List[Dict], schema: Dict) -> bool:
        """Validate JSON data against a schema."""
        # Basic validation - can be extended with jsonschema library
        if not data:
            return True
        
        required_fields = schema.get('required_fields', [])
        
        for i, item in enumerate(data):
            missing_fields = set(required_fields) - set(item.keys())
            if missing_fields:
                log.error(f"Item {i} missing required fields: {missing_fields}")
                return False
        
        return True


class YAMLDataProvider(DataProvider):
    """Data provider for YAML files."""
    
    def load_data(self, source: str) -> List[Dict[str, Any]]:
        """Load data from a YAML file."""
        source_path = Path(source)
        
        if not source_path.exists():
            raise FileNotFoundError(f"YAML file not found: {source}")
        
        try:
            with open(source_path, 'r', encoding='utf-8') as yamlfile:
                data = yaml.safe_load(yamlfile)
            
            # Ensure data is a list of dictionaries
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                raise ValueError("YAML data must be a list of objects or a single object")
            
            # Validate that all items are dictionaries
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    raise ValueError(f"Item {i} in YAML data is not an object")
            
            log.info(f"Loaded {len(data)} items from YAML file: {source}")
            return data
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in file {source}: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load YAML file {source}: {e}")
    
    def validate_data_schema(self, data: List[Dict], schema: Dict) -> bool:
        """Validate YAML data against a schema."""
        # Basic validation - similar to JSON
        if not data:
            return True
        
        required_fields = schema.get('required_fields', [])
        
        for i, item in enumerate(data):
            missing_fields = set(required_fields) - set(item.keys())
            if missing_fields:
                log.error(f"Item {i} missing required fields: {missing_fields}")
                return False
        
        return True


class DataProviderFactory:
    """Factory for creating data providers based on file extension."""
    
    _providers = {
        '.csv': CSVDataProvider,
        '.json': JSONDataProvider,
        '.yaml': YAMLDataProvider,
        '.yml': YAMLDataProvider,
    }
    
    @classmethod
    def create_provider(cls, source: str) -> DataProvider:
        """Create a data provider based on the file extension."""
        source_path = Path(source)
        extension = source_path.suffix.lower()
        
        provider_class = cls._providers.get(extension)
        if not provider_class:
            raise ValueError(f"Unsupported data file format: {extension}")
        
        return provider_class()
    
    @classmethod
    def register_provider(cls, extension: str, provider_class: type):
        """Register a custom data provider for a file extension."""
        cls._providers[extension] = provider_class


def load_test_data(source: str, schema: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """Convenience function to load test data from any supported format."""
    provider = DataProviderFactory.create_provider(source)
    data = provider.load_data(source)
    
    if schema:
        if not provider.validate_data_schema(data, schema):
            raise ValueError(f"Data validation failed for {source}")
    
    return data