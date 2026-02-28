import json
import yaml
from subprocess import Popen

def parse_lab_devices(devicesFile: str,
                      credsFile: str,
                      method: str) -> dict[str, dict[str, str]]:
    """Helper function to parse the rendered JSON file from the node-data commands in this utility
    to extract the required information for connectivity to lab devices"""
    with open(devicesFile, "r") as df, open(credsFile, "r") as cf:
        devices = json.load(df)
        creds = yaml.safe_load(cf)

    metadata = devices["_metadata_"]
    del devices["_metadata_"]

    output = {}
    for _, deviceList in devices.items():
        for device in deviceList:
            deviceDict = {}
            match method:
                case "dns":
                    deviceDict["address"] = device["name"]
                case "ipv4":
                    deviceDict["address"] = device["ipv4_address"]
                case "ipv6":
                    deviceDict["address"] = device["ipv6_address"]
                case "clabhost":
                    deviceDict["address"] = metadata["clabHost"]

            deviceDict["ports"] = device["ports"]

            conditions = [f'node={device["name"]}', f'image={device["image"]}', f'kind={device["kind"]}', "default"]
            for condition in conditions:
                try:
                    for val in ["username", "password"]:
                        deviceDict[val] = creds[condition][val]
                    break
                except KeyError:
                    continue

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