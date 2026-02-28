from typing import Any
from requests import Response, Session
import requests.exceptions
import json

class ContainerlabAPI(Session):
    def __init__(self, baseURL: str) -> None:
        self.baseURL = baseURL
        super().__init__()

    def request(self, method: str, url: str, *args, **kwargs) -> Response:
        try:
            return super().request(method, f"{self.baseURL}{url}", *args, **kwargs)
        except requests.exceptions.RequestException as e:
            print(f"Error while attempting to connect to the Containerlab API: {e}")
            exit(-1)

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
    try:
        with open(outputfile, "w") as file:
            file.write(json.dumps(data, indent=4))
    except OSError as e:
        print(f"Error, unable to write output to file {outputfile}: {e}")
        exit(-1)
    print(f"Output successfully written to {outputfile}")