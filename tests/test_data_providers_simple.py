"""
Simple tests for data providers.
"""
import pytest
import tempfile
import json
import csv
from pathlib import Path
from dact.data_providers import CSVDataProvider, JSONDataProvider, load_test_data


def test_json_data_provider():
    """Test JSON data provider."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_data = [
            {"name": "test1", "value": 10, "expected": True},
            {"name": "test2", "value": 20, "expected": False}
        ]
        json.dump(test_data, f)
        json_file = f.name
    
    try:
        provider = JSONDataProvider()
        data = provider.load_data(json_file)
        
        assert len(data) == 2
        assert data[0]['name'] == 'test1'
        assert data[0]['value'] == 10
        assert data[1]['expected'] == False
    finally:
        Path(json_file).unlink()


def test_csv_data_provider():
    """Test CSV data provider."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'value', 'expected'])
        writer.writerow(['test1', '10', 'true'])
        writer.writerow(['test2', '20', 'false'])
        csv_file = f.name
    
    try:
        provider = CSVDataProvider()
        data = provider.load_data(csv_file)
        
        assert len(data) == 2
        assert data[0]['name'] == 'test1'
        assert data[0]['value'] == 10  # Should be converted to int
        assert data[1]['expected'] == False  # Should be converted to bool
    finally:
        Path(csv_file).unlink()


def test_load_test_data_convenience():
    """Test the convenience function for loading test data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_data = [{"name": "test1", "value": 10}]
        json.dump(test_data, f)
        json_file = f.name
    
    try:
        data = load_test_data(json_file)
        
        assert len(data) == 1
        assert data[0]['name'] == 'test1'
    finally:
        Path(json_file).unlink()