import json

import yaml
from subprocess import Popen

from ..misc.helpers import read_object_from_structured_data, retrieve_and_delete_metadata, check_if_list, handle_dict_access_errors

def parse_lab_devices(devicesFile: str,
                      credsFile: str,
                      method: str) -> dict[str, dict[str, str]]:
    """Helper function to parse the rendered JSON file from the node-data commands in this utility
    to extract the required information for connectivity to lab devices"""
    try:
        devices = read_object_from_structured_data(filename=devicesFile, expected_format="json")
        creds = read_object_from_structured_data(filename=credsFile, expected_format="yaml")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error while importing lab devices from {devicesFile}: {e}")
        exit(-1)
    except yaml.YAMLError as e:
        print(f"Error while importing lab device credentials from {credsFile}: {e}")
        exit(-1)

    metadata = retrieve_and_delete_metadata(data=devices, filename=devicesFile)

    output = {}
    for lab, deviceList in devices.items():
        for idx, device in enumerate(check_if_list(data=deviceList, errorString=f"Error parsing device list for {lab} in {devicesFile}")):
            deviceDict = {}
            try:
                deviceDict["name"] = device["name"]
                if device["method"] == "clabHost":
                    deviceDict["address"] = metadata["clabHost"]
                else:
                    match method:
                        case "dns":
                            deviceDict["address"] = device["name"]
                        case "ipv4":
                            deviceDict["address"] = device["ipv4_address"]
                        case "ipv6":
                            deviceDict["address"] = device["ipv6_address"]

                deviceDict["ports"] = device["ports"]

                conditions = [f'node={device["name"]}', f'image={device["image"]}', f'kind={device["kind"]}', "default"]
            except (KeyError, TypeError) as e:
                handle_dict_access_errors(exception=e, errorString=f"Error parsing data for device #{idx + 1} in {devicesFile}")

            for condition in conditions:
                try:
                    for val in ["username", "password"]:
                        deviceDict[val] = creds[condition][val]
                    break
                except KeyError:
                    continue
                except TypeError as e:
                    handle_dict_access_errors(exception=e, errorString=f"Error while processing credentials for {condition} in {credsFile}")

            if "username" not in deviceDict:
                print(f'Error: Unable to retrieve username for device {device["name"]}')
                exit(-1)

            if "password" not in deviceDict:
                deviceDict["password"] = None
                print(f'Warning: Unable to retrieve password for device {device["name"]}. Password autofill won\'t be available for this device')

            output[device["name"]] = deviceDict

    return output

def run_command(cmd: list[str], executable: str) -> None:
    """Helper function used by launch commands to run a command/start a process using
    the provided list of arguments and executable name and handle standard errors"""
    try:
        Popen(cmd)
    except FileNotFoundError:
        print(f"Error running launch command: {executable} not found. Try the following steps:\n(1) Running the executable provided directly in the shell to test its functionality\n(2) Using an absolute path, if you are using a relative path\n(3) Confirming that the file exists and that your user has permission to view/execute it")
        exit(-1)