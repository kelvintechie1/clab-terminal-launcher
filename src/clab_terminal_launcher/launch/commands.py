from functools import wraps
from typing import Callable
import shlex
from xml.etree import ElementTree as ET
from shutil import copy

import click
from .helpers import parse_lab_devices, run_command

def launch_type(f: Callable) -> Callable:
    """Wrapper function/decorator that includes standardized functionality for all launch types/methods (i.e., all terminal emulators, etc.)"""
    @click.option("--inputfile", "-i", required=True,
                  help="Specify the path to the input JSON file containing running nodes")
    @click.option("--creds", "-c", required=True,
                  help="Specify the path to the input YAML file containing device credentials")
    @click.option("--method", "-m", type=click.Choice(["dns", "ipv4", "ipv6", "clabhost"]), default="dns",
                  help="Specifies whether to use DNS hostnames, IPv4 addresses, IPv6 addresses, or the Containerlab host's DNS name/IP address to connect to lab devices in Containerlab; default is DNS")
    @wraps(f)
    def wrapper(inputfile: str, creds: str, method: str, jumphost: str | None = None, **kwargs):

        devices = parse_lab_devices(devicesFile=inputfile, credsFile=creds, method=method)

        if f.__name__ in ["MTPuTTY"]:
            f(**kwargs, jumphost=jumphost, devices=devices)
            return

        print(f"Preparing to launch {f.__name__.replace('_', ' ')} sessions for {len(devices)} devices from {inputfile}...")
        print(f"Using jumphost: {jumphost}" if jumphost is not None else "Not using a jumphost; connecting via localhost")

        for name, node in devices.items():
            print(f'Launching SSH session to device {name} using address {node["address"]}, port {node["ports"]["ssh"]}, username {node["username"]}{f", password {node["password"]}" if node["password"] is not None else ""}')
            f(**kwargs, jumphost=jumphost, node=node)
    return wrapper

@click.group()
def launch() -> None:
    """Automatically launch sessions to connect to lab devices"""
    pass

@launch.command()
@launch_type
@click.option("--session", "-s", "jumphost",
              help="Specify the name of the jumphost session in SecureCRT (e.g., the session for the Containerlab host itself) using path notation (i.e., a session called s stored under a folder called f would be notated as f\\s")
@click.option("--executable", "-e", default="securecrt",
              help="Specify the path/command to run the SecureCRT executable; default: securecrt")
def SecureCRT(jumphost: str | None, executable: str, node: dict[str, str]) -> None:
    """Launch SecureCRT terminals to lab devices"""
    cmd = [f'{executable}', '/T', '/ssh2', f'{node["address"]}', '/l', f'{node["username"]}', '/P', f'{node["ports"]["ssh"]}', '/accepthostkeys']
    if node["password"] is not None:
        cmd[6:6] = ['/password', f'{node["password"]}']
    if jumphost is not None:
        cmd.insert(1, f'/firewall=Session:{jumphost}')
    run_command(cmd=cmd, executable=executable)

@launch.command()
@launch_type
@click.option("--session", "-s", "jumphost",
              help="Specify the name of the jumphost session in PuTTY (e.g., the session for the Containerlab host itself)")
@click.option("--executable", "-e", default="putty",
              help="Specify the path/command to run the PuTTY executable; default: putty")
def PuTTY(jumphost: str | None, executable: str, node: dict[str, str]) -> None:
    """Launch windowed PuTTY terminals to lab devices"""
    cmd = [f'{executable}', '-ssh', f'{node["address"]}', '-l', f'{node["username"]}', '-P', f'{node["ports"]["ssh"]}']
    if node["password"] is not None:
        cmd[6:6] = ['-pw', f'{node["password"]}']
    if jumphost is not None:
        cmd[1:1] = ['-load', f'{jumphost}']
    run_command(cmd=cmd, executable=executable)

@launch.command()
@launch_type
@click.option("--session", "-s", "jumphost",
              help="Specify the name of the jumphost session in PuTTY (e.g., the session for the Containerlab host itself)")
@click.option("--config", "-f", default="%appdata%\\TTYPlus\\mtputty.xml",
              help="Specify the path/location of the mtputty.xml configuration file; defaults to the normal location (%appdata%\\TTYPlus\\mtputty.xml); unless you are using the portable version or the XML file is referenced in a different place on your system (e.g., if you are running this script from WSL), you likely don't need to specify this option")
def MTPuTTY(jumphost: str | None, config: str, devices: dict[str, dict[str, str]]) -> None:
    """Create MTPuTTY terminal sessions for lab devices (sessions must still be manually launched from MTPuTTY GUI)"""
    copy(src=config, dst="mtputty_backup.xml")
    print("Backup of the MTPuTTY configuration successfully created in the \"mtputty_backup.xml\" file in the current directory")
    tree = ET.parse(config)
    servers = tree.find("./Servers/Putty")
    for server in list(servers):
        if server.find("DisplayName").text in devices:
            print(f"Removing existing session {server.find("DisplayName").text} from MTPuTTY database...")
            servers.remove(server)

    print(f"Using jumphost: {jumphost}" if jumphost is not None else "Not using a jumphost; connecting via localhost")

    for name, node in devices.items():
        server = ET.SubElement(servers, "Node")
        server.attrib["Type"] = "1"
        ET.SubElement(server, "SavedSession").text = jumphost if jumphost is not None else "Default Settings"
        ET.SubElement(server, "DisplayName").text = name
        ET.SubElement(server, "ServerName").text = node["address"]
        ET.SubElement(server, "Port").text = node["ports"]["ssh"]
        ET.SubElement(server, "UserName").text = node["username"]
        if node["password"] is not None:
            ET.SubElement(server, "Password").text = node["password"]
        ET.SubElement(server, "CLParams").text = f'{f"-load {jumphost} " if jumphost is not None else ""}-l {node["username"]}{" -pw *****" if node["password"] is not None else ""} {node["address"]} -P {node["ports"]["ssh"]}'
        print(f"Creating session {name} in MTPuTTY database with address {node['address']}, port {node['port']}, username {node['username']}{f", password {node['password']}" if node["password"] is not None else ""}...")

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
def native_OpenSSH(jumphost: str | None, executable: str, node: dict[str, str], terminal: str) -> None:
    """Launch terminal sessions to lab devices using OpenSSH and your native terminal of choice (NOTE: password autofill is NOT available for this option)"""
    ssh_cmd = [f'{executable}', '-l', f'{node["username"]}', '-p', f'{node["ports"]["ssh"]}', f'{node["address"]}']
    if jumphost is not None:
        ssh_cmd[1:1] = ['-J', f'{jumphost}']

    cmd = shlex.split(terminal) + ssh_cmd
    run_command(cmd=cmd, executable=executable)