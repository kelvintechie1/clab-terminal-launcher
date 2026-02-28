import json
import yaml

import click
from dotenv import load_dotenv
import os

from requests import Session
import requests.exceptions
from getpass import getpass

from .helpers import process_response, write_common_metadata, write_output_to_file

@click.group()
def node_data() -> None:
    """Process data for running Containerlab nodes

    REQUIRED prior to using the launch commands"""
    pass

@node_data.command()
@click.option("--lab", "-l", "labs", multiple=True, help="Specify labs to look for; include this option multiple times to specify multiple labs")
@click.option("--host", "-h", "clabHost", default="localhost", help="Specify the IP address/DNS hostname of the Containerlab host; defaults to localhost (you do not need to include this option if Containerlab is running locally)")
@click.option("--username", "-u", required=True, help="Specify the username of the Linux user used to authenticate to Containerlab")
@click.option("--password", "-p", help="Specify the password of the Linux user used to authenticate to Containerlab; OPTIONAL. NOT RECOMMENDED. WARNING: INSECURE. USE THE CLABPASS ENVIRONMENT VARIABLE (EITHER EXPORTED THROUGH THE SHELL OR VIA A .ENV FILE IN THE LOCAL DIRECTORY) OR TYPE THE PASSWORD INTERACTIVELY. REFER TO THE DOCS FOR MORE DETAILS.")
@click.option("--outputfile", "-o", required=True, help="Specify the path to the output file to which to write the running node information in JSON format")
def retrieve_from_api(clabHost: str, outputfile: str, labs: tuple[str], username: str, password: str | None = None) -> None:
    """Get details about running nodes from Containerlab API"""
    api = Session()
    baseURL = f"http://{clabHost}:8080"
    # Authenticate to the API
    try:
        print(f"Authenticating to the Containerlab API at host {clabHost}...")

        if password is None:
            load_dotenv()
            password = os.getenv("CLABPASS")
            if password is not None:
                print("Password retrieved via environment variable.")

        api.headers["Authorization"] = f"Bearer {process_response(error="Error authenticating to the Containerlab API",
                                                                  host=clabHost,
                                                                  response=api.post(url=f"{baseURL}/login",
                                                                                    json={"username": username,
                                                                                          "password": password if password is not None else getpass("Enter your Containerlab host password:")}))["token"]}"
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to the Containerlab API: {e}")
        exit(-1)

    # Retrieve nodes for running labs
    allNodes = {}
    if labs: # runs if there is a list of labs provided
        for lab in labs:
            print(f"Retrieving running nodes for lab {lab}...")
            allNodes[lab] = process_response(error=f"Error retrieving lab nodes for lab {lab} - check to make sure the lab exists and is running",
                                          host=clabHost,
                                          response=api.get(url=f"{baseURL}/api/v1/labs/{lab}"))
    else: # runs to retrieve all labs as a default behavior without a list of labs
        print("Retrieving running nodes for all labs...")
        allNodes = process_response(error="Error retrieving all running labs",
                                 host=clabHost,
                                 response=api.get(url=f"{baseURL}/api/v1/labs"))
        if not allNodes:
            print("No running labs found - check to make sure there are labs running")
            exit(-1)

        print(f"Labs found: {", ".join(allNodes)}")

    # Filter for running nodes only
    runningNodes = {k: [(node | {"ports": {"ssh": 22}}) for node in v if node["state"] == "running"] for k, v in allNodes.items()}
    parsedOutput = write_common_metadata(host=clabHost, originalDict=runningNodes)
    write_output_to_file(outputfile=outputfile, data=parsedOutput)

@node_data.command()
@click.option("--host", "-h", "clabHost", default="localhost", help="Specify the IP address/DNS hostname of the Containerlab host; defaults to localhost (you do not need to include this option if Containerlab is running locally)")
@click.option("--inputfile", "-i", required=True, help="Specify the path to the input JSON file containing node(s) for one or more labs")
@click.option("--outputfile", "-o", required=True, help="Specify the path to the output JSON file to which to write the output containing running node information in JSON format")
def parse_inspect_output(inputfile: str, outputfile: str, clabHost: str) -> None:
    """Process clab inspect output for details about running nodes"""
    with open(inputfile, "r") as file:
        data = json.load(file)

    parsedOutput = {}
    for name, nodes in data.items():
        print(f"Parsing output for lab {name}...")
        parsedOutput[name] = [{"name": node["Labels"]["clab-node-longname"],
                               "image": node["Image"],
                               "kind": node["Labels"]["clab-node-kind"],
                               "state": node["State"],
                               "ipv4_address": node["NetworkSettings"]["IPv4addr"],
                               "ipv6_address": node["NetworkSettings"]["IPv6addr"],
                               "ports": {
                                   "ssh": 22
                               }}
                              for node in nodes if node["State"] == "running"]

    finalOutput = write_common_metadata(host=clabHost, originalDict=parsedOutput)

    with open(outputfile, "w") as file:
        write_output_to_file(outputfile=outputfile, data=finalOutput)

@node_data.command()
@click.option("--portfile", "-p", required=True,
              help="Specify the path to the input YAML file containing the port numbers for nodes with custom/non-default port numbers")
@click.option("--datafile", "-d", required=True,
              help="Specify the path to the rendered JSON file containing running nodes that was generated by this utility using another node-data command")
@click.option("--output", "-o",
              help="Specify the output path for the new, rendered JSON file containing the custom ports for applicable running nodes; OPTIONAL, default is to replace the existing file. Only use this option if you care about keeping both the original and newly rendered JSON files")
def inject_custom_ports(output: str | None, portfile: str, datafile: str) -> None:
    """Customize port numbers for sessions to lab devices in rendered output

    REQUIRES rendered output generated by this utility using another node-data command"""
    with open(portfile, "r") as pf, open(datafile, "r") as df:
        data = json.load(df)
        ports = yaml.safe_load(pf)

    metadata = data["_metadata_"]
    del data["_metadata_"]
    nodeNames = {lab: [node["name"] for node in nodes] for lab, nodes in data.items()}
    for lab, nodes in ports.items():
        for name, ports in nodes.items():
            print(f"Changing SSH port number for node {name} to {ports['ssh']}...")
            data[lab][nodeNames[lab].index(name)]["ports"]["ssh"] = ports["ssh"]

    fileName = output if output is not None else datafile
    with open(fileName, "w") as df:
        df.write(json.dumps({"_metadata_": metadata} | data, indent=4))
        print(f"Output with custom port numbers written to {fileName}")