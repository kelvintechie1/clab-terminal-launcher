import json
import yaml
from typing import Any

def check_if_list(data: Any, errorString: str) -> list[Any]:
    """Helper function to check whether the provided data is of the list type; print an error message
    and exit the program if not"""
    if isinstance(data, list):
        return data

    print(f"{errorString}: Not an array/list")
    exit(-1)

def handle_dict_access_errors(exception: Exception, errorString: str) -> None:
    """Helper function to handle two common types of errors (key and type errors) that arise when
    trying to access invalid dictionaries by printing the correct error message and exiting"""
    if issubclass(type(exception), KeyError):
        print(f"{errorString}: the following fields/keys were not found, {exception}")
    elif issubclass(type(exception), TypeError):
        print(f"{errorString}: invalid type, the item is not a dictionary/object/mapping; {exception}")
    exit(-1)

def read_object_from_structured_data(expected_format: str, filename: str) -> dict[str, Any] | None:
    """Helper function to read objects/mappings from structured data formats (e.g., JSON/YAML)
    and return them in dictionary form, raising an exception if the provided data is not an object/mapping
    and handling other exceptions that arise while reading the file"""
    errorString = f"Error while reading {filename}"
    match expected_format:
        case "json":
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        raise ValueError("Invalid format: NOT a JSON object")
                    return data
            except OSError as e:
                print(f"{errorString}: {e}")
                exit(-1)
        case "yaml":
            try:
                with open(filename, "r") as f:
                    data = yaml.safe_load(f)
                    if not isinstance(data, dict):
                        raise yaml.YAMLError("Invalid format: NOT a YAML mapping/object")
                    return data
            except OSError as e:
                print(f"{errorString}: {e}")
                exit(-1)
        case _:
            return None

def retrieve_and_delete_metadata(data: dict[str, Any], filename: str) -> dict[str, Any]:
    """Helper function to return the data contained as the value of the _metadata_ key from JSON objects rendered
    by this utility and delete the _metadata_ key in the original JSON object, such that other functions
    in the utility not expecting the _metadata_ key don't experience any issues; raises an exception
    if the _metadata_ key cannot be found, as it is mandatory"""
    try:
        metadata = data["_metadata_"]
        del data["_metadata_"]
        return metadata
    except KeyError:
        print(f"Error: Unable to retrieve the required _metadata_ field from {filename}")
        exit(-1)