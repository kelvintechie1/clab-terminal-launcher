from typing import Any
from requests import Response
import json

def process_response(error: str, host: str, response: Response) -> dict[str, Any] | None:
    """Helper function to parse responses from the Containerlab API to determine the status of the
    response and handle any API errors by outputting the error and terminating the program"""
    if response.status_code == 200:
        return response.json()
    else:
        try:
            returnedError = response.json()["error"]
        except json.JSONDecodeError:
            returnedError = response.text
        print(f"{error}, host: {host}, status code: {response.status_code}, error: {returnedError}")
        exit(-1)

def write_common_metadata(host: str, originalDict: dict[str, Any]) -> dict[str, Any]:
    """Helper function to write a common set of Containerlab metadata to the rendered JSON file"""
    metadata = {
        "_metadata_": {
            "clabHost": host
        }
    }

    return metadata | originalDict

def write_output_to_file(outputfile: str, data: dict[str, Any]) -> None:
    """Helper function to write rendered JSON output to an output file and report the status"""
    with open(outputfile, "w") as file:
        file.write(json.dumps(data, indent=4))
    print(f"Output successfully written to {outputfile}")