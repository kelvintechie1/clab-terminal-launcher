import json
import yaml
from functools import wraps
from subprocess import run
from typing import Callable

import click

def parse_lab_devices(devices: dict[str, list[dict[str, str]]],
                      creds: dict[str, dict[str, str]],
                      method: str) -> dict[str, dict[str, str]]:
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

            conditions = [f'node={device["name"]}', f'image={device["image"]}', f'kind={device["kind"]}']
            for condition in conditions:
                try:
                    for val in ["username", "password"]:
                        deviceDict[val] = creds[condition][val]
                except KeyError:
                    continue

                if (deviceDict["username"] is None) or (deviceDict["password"] is None):
                    print(f'Error: Unable to retrieve username/password for device {device["name"]}; Username value: {deviceDict["username"]}; Password value: {deviceDict["password"]}')
                    exit(-1)

            output[device["name"]] = deviceDict

    return output

def launch_type(f: Callable) -> Callable:
    @wraps(f)
    @click.option("--inputfile", "-i", required=True,
                  help="Specify the path to the input JSON file containing running nodes")
    @click.option("--creds", "-c", required=True,
                  help="Specify the path to the input YAML file containing device credentials")
    @click.option("--method", "-m", type=click.Choice(["dns", "ipv4", "ipv6"]), default="dns",
                  help="Specifies whether to use DNS, IPv4, or IPv6 addresses to connect to lab devices in Containerlab; default is DNS")
    def wrapper(host: str, inputfile: str, method: str, creds: str):
        with open(inputfile, "r") as file:
            devices = json.load(file)
        with open(creds, "r") as file:
            creds = yaml.safe_load(file)

        parse_lab_devices(devices=devices, creds=creds, method=method)
        f(host, inputfile)
    return wrapper

@click.group()
def launch():
    pass

@launch.command()
@launch_type
@click.option("--session", "-s",
              help="Specify the name of the jumphost session in SecureCRT (e.g., the session for the Containerlab host itself) using path notation (i.e., a session called s stored under a folder called f would be notated as f\s")
def securecrt(session: str, inputfile: str, devices: dict[str, dict[str, str]]) -> None:
    print(f"Preparing to launch SecureCRT sessions for {len(devices)} devices from {inputfile}...")
    print(f"Using jumphost: {session}")
    for name, node in devices.items():
        print(f'Launching SSH session to device {name} using address {node["address"]}, username {node["username"]}, and password {node["password"]}')
        run(['securecrt', '/T', f'/firewall=Session:{session}', '/ssh2', f'{node["address"]}', '/l', f'{node["username"]}', '/password', f'{node["password"]}', '/accepthostkeys'])