import json
import yaml
from functools import wraps
from subprocess import Popen
from typing import Callable
import shlex
from xml.etree import ElementTree as ET
from shutil import copy

import click

def parse_lab_devices(devicesFile: str,
                      credsFile: str,
                      method: str) -> dict[str, dict[str, str]]:

    with open(devicesFile, "r") as df, open(credsFile, "r") as cf:
        devices = json.load(df)
        creds = yaml.safe_load(cf)

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
                    break
                except KeyError:
                    continue

            check = {k: (k in deviceDict) for k in ("username", "password")}
            if not all(check.values()):
                print(f'Error: Unable to retrieve username/password for device {device["name"]}; {", ".join([f"{k.capitalize()} Present: {v}" for k, v in check.items()])}')
                exit(-1)

            output[device["name"]] = deviceDict

    return output

def launch_type(f: Callable) -> Callable:
    @click.option("--inputfile", "-i", required=True,
                  help="Specify the path to the input JSON file containing running nodes")
    @click.option("--creds", "-c", required=True,
                  help="Specify the path to the input YAML file containing device credentials")
    @click.option("--method", "-m", type=click.Choice(["dns", "ipv4", "ipv6"]), default="dns",
                  help="Specifies whether to use DNS, IPv4, or IPv6 addresses to connect to lab devices in Containerlab; default is DNS")
    @wraps(f)
    def wrapper(inputfile: str, creds: str, method: str, jumphost: str | None = None, *args, **kwargs):

        devices = parse_lab_devices(devicesFile=inputfile, credsFile=creds, method=method)

        print(f"Preparing to launch {f.__name__.replace('_', ' ')} sessions for {len(devices)} devices from {inputfile}...")
        print(f"Using jumphost: {jumphost}" if jumphost is not None else "Not using a jumphost; connecting via localhost")

        for name, node in devices.items():
            print(f'Launching SSH session to device {name} using address {node["address"]}, username {node["username"]}, and password {node["password"]}')
            f(**kwargs, jumphost=jumphost, node=node)
    return wrapper

def run_command(cmd: list[str], executable: str) -> None:
    try:
        Popen(cmd)
    except FileNotFoundError:
        print(f"Error running launch command: {executable} not found. Try the following steps:\n(1) Running the executable provided directly in the shell to test its functionality\n(2) Using an absolute path, if you are using a relative path\n(3) Confirming that the file exists and that your user has permission to view/execute it")
        exit(-1)

@click.group()
def launch():
    pass

@launch.command()
@launch_type
@click.option("--session", "-s", "jumphost",
              help="Specify the name of the jumphost session in SecureCRT (e.g., the session for the Containerlab host itself) using path notation (i.e., a session called s stored under a folder called f would be notated as f\\s")
@click.option("--executable", "-e", default="securecrt",
              help="Specify the path/command to run the SecureCRT executable; default: securecrt")
def SecureCRT(jumphost: str | None, executable: str, node: dict[str, str]) -> None:
    cmd = [f'{executable}', '/T', '/ssh2', f'{node["address"]}', '/l', f'{node["username"]}', '/password', f'{node["password"]}', '/accepthostkeys']
    if jumphost is not None:
        cmd.insert(1, f'/firewall=Session:{jumphost}')
    run_command(cmd=cmd, executable=executable)

@launch.command()
@launch_type
@click.option("--session", "-s", "jumphost",
              help="Specify the name of the jumphost session in PuTTY (e.g., the session for the Containerlab host itself)")
@click.option("--executable", "-e", default="putty",
              help="Specify the path/command to run the PuTTY executable; default: putty")
def PuTTY(jumphost: str | None, executable: str, node: dict[str, str]):
    cmd = [f'{executable}', '-ssh', f'{node["address"]}', '-l', f'{node["username"]}', '-pw', f'{node["password"]}']
    if jumphost is not None:
        cmd = [cmd[0]] + ['-load', f'{jumphost}'] + cmd[1:]
    run_command(cmd=cmd, executable=executable)

@launch.command()
@click.option("--inputfile", "-i", required=True,
              help="Specify the path to the input JSON file containing running nodes")
@click.option("--creds", "-c", required=True,
              help="Specify the path to the input YAML file containing device credentials")
@click.option("--method", "-m", type=click.Choice(["dns", "ipv4", "ipv6"]), default="dns",
              help="Specifies whether to use DNS, IPv4, or IPv6 addresses to connect to lab devices in Containerlab; default is DNS")
@click.option("--session", "-s", "jumphost",
              help="Specify the name of the jumphost session in PuTTY (e.g., the session for the Containerlab host itself)")
@click.option("--config", "-f", default="%appdata%\\TTYPlus\\mtputty.xml",
              help="Specify the path/location of the mtputty.xml configuration file; defaults to the normal location (%appdata%\\TTYPlus\\mtputty.xml); unless you are using the portable version or the XML file is referenced in a different place on your system (e.g., if you are running this script from WSL), you likely don't need to specify this option")
def MTPuTTY(jumphost: str | None, config: str, method: str, creds: str, inputfile: str):

    devices = parse_lab_devices(devicesFile=inputfile, credsFile=creds, method=method)

    copy(src=config, dst="mtputty_backup.xml")
    print(f"Backup of the MTPuTTY configuration successfully created in the \"mtputty_backup.xml\" file in the current directory")
    tree = ET.parse(config)
    servers = tree.find("./Servers/Putty")
    for server in list(servers):
        if server.find("DisplayName").text in devices:
            print(f"Removing existing session {server.find("DisplayName").text} from MTPuTTY database...")
            servers.remove(server)

    for name, node in devices.items():
        server = ET.SubElement(servers, "Node")
        server.attrib["Type"] = "1"
        ET.SubElement(server, "SavedSession").text = jumphost if jumphost is not None else "Default Settings"
        ET.SubElement(server, "DisplayName").text = name
        ET.SubElement(server, "ServerName").text = node["address"]
        ET.SubElement(server, "UserName").text = node["username"]
        ET.SubElement(server, "Password").text = node["password"]
        ET.SubElement(server, "CLParams").text = f'{f"-load {jumphost} " if jumphost is not None else ""}-l {node["username"]} -pw ***** {node["address"]}'
        print(f"Creating session {name} in MTPuTTY database...")

    tree.write(config)
    print(f"New MTPuTTY configuration successfully written to {config}")

@launch.command()
@launch_type
@click.option("--session", "-s", "jumphost",
              help="Specify the name of the jumphost (i.e., your Containerlab host), as defined in the OpenSSH client config file")
@click.option("--executable", "-e", default="ssh",
              help="Specify the path/command to run the OpenSSH client executable")
@click.option("--terminal", "-t", required=True,
              help="Specify the exact command to execute your terminal of choice, INCLUDING any flags/options/parameters; this will be prepended to the OpenSSH command (i.e., <terminal command> <ssh command>)")
def native_OpenSSH(jumphost: str | None, executable: str, node: dict[str, str], terminal: str):
    ssh_cmd = [f'{executable}', '-l', f'{node["username"]}', f'{node["address"]}']
    if jumphost is not None:
        ssh_cmd = [ssh_cmd[0]] + ['-J', f'{jumphost}'] + ssh_cmd[1:]

    cmd = shlex.split(terminal) + ssh_cmd
    run_command(cmd=cmd, executable=executable)