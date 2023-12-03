def find_value(json_data, key):
    if isinstance(json_data, dict):
        for k, v in json_data.items():
            if k == key:
                return v
            if isinstance(v, (dict, list)):
                result = find_value(v, key)
                if result is not None:
                    return result
    elif isinstance(json_data, list):
        for item in json_data:
            result = find_value(item, key)
            if result is not None:
                return result
    return None
