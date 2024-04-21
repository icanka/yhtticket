"""Utility functions for the API."""

def find_value(json_data, key):
    """Find the value of the given key in the JSON data."""
    if isinstance(json_data, dict):
        for k, v in json_data.items():
            if k == key:
                return v
            if isinstance(v, (dict, list)):
                result = find_value(v, key)

    elif isinstance(json_data, list):
        for item in json_data:
            result = find_value(item, key)
    return result
