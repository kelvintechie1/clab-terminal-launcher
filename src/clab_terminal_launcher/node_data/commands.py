import json
import yaml
import click
from dotenv import dotenv_values
import os
from getpass import getpass
from .helpers import process_response, write_common_metadata, write_output_to_file, ContainerlabAPI
from ..misc.helpers import read_object_from_structured_data, retrieve_and_delete_metadata, check_if_list, handle_dict_access_errors


@click.group()
def node_data() -> None:
    """Process data for running Containerlab nodes

    REQUIRED prior to using the launch commands"""
    pass

@node_data.command()
@click.option("--envfile", "-e",
              help="OPTIONAL; specify the path to the plain text Bash-style environment variable file where the password is contained as the CLABPASS variable; if specified, takes precedence over default behavior of using system-defined environment variable")
@click.option("--host", "-h", "clabHost", default="localhost",
              help="Specify the IP address/DNS hostname of the Containerlab host; defaults to localhost (you do not need to include this option if Containerlab is running locally)")
@click.option("--labs", "-l", "labs",
              help="Specify labs to look for; specify multiple labs as a comma-separated list")
@click.option("--outputfile", "-o", required=True,
              help="Specify the path to the output file to which to write the running node information in JSON format")
@click.option("--username", "-u", required=True,
              help="Specify the username of the Linux user used to authenticate to Containerlab")
@click.option("--password", "-p",
              help="Specify the password of the Linux user used to authenticate to Containerlab; OPTIONAL. NOT RECOMMENDED. WARNING: INSECURE. USE THE CLABPASS ENVIRONMENT VARIABLE (EITHER EXPORTED THROUGH THE SHELL OR VIA A .ENV FILE IN THE LOCAL DIRECTORY) OR TYPE THE PASSWORD INTERACTIVELY. REFER TO THE DOCS FOR MORE DETAILS.")
def retrieve_from_api(envfile: str | None, clabHost: str, outputfile: str, labs: str, username: str, password: str | None = None) -> None:
    """Get details about running nodes from Containerlab API"""
    api = ContainerlabAPI(baseURL=f"http://{clabHost}:8080")
    # Authenticate to the API
    print(f"Authenticating to the Containerlab API at host {clabHost}...")

    if password is None:
        if envfile is not None:
            try:
                password = dotenv_values(envfile)["CLABPASS"]
            except KeyError:
                print(f"WARNING: CLABPASS variable not found in provided environment variable file {envfile}. Proceeding without it...")
        else:
            password = os.getenv("CLABPASS")
        if password is not None:
            print("Password retrieved via environment variable.")

    api.headers["Authorization"] = f"Bearer {process_response(error="Error authenticating to the Containerlab API",
                                                              host=clabHost,
                                                              response=api.post(url="/login",
                                                                                json={"username": username,
                                                                                      "password": password if password is not None else getpass("Enter your Containerlab host password:")}))["token"]}"

    # Retrieve nodes for running labs
    allNodes = {}
    if labs: # runs if there is a list of labs provided
        for lab in labs.replace(" ", "").split(","):
            print(f"Retrieving running nodes for lab {lab}...")
            allNodes[lab] = process_response(error=f"Error retrieving lab nodes for lab {lab} - check to make sure the lab exists and is running",
                                          host=clabHost,
                                          response=api.get(url="/api/v1/labs/{lab}"))
    else: # runs to retrieve all labs as a default behavior without a list of labs
        print("Retrieving running nodes for all labs...")
        allNodes = process_response(error="Error retrieving all running labs",
                                 host=clabHost,
                                 response=api.get(url="/api/v1/labs"))
        if not allNodes:
            print("No running labs found - check to make sure there are labs running")
            exit(-1)

        print(f"Labs found: {", ".join(allNodes)}")

    # Filter for running nodes only
    runningNodes = {k: [(node | {"ports": {"ssh": 22}, "method": None}) for node in v if node["state"] == "running"] for k, v in allNodes.items()}
    write_output_to_file(outputfile=outputfile, data=write_common_metadata(host=clabHost, originalDict=runningNodes))

@node_data.command()
@click.option("--host", "-h", "clabHost", default="localhost",
              help="Specify the IP address/DNS hostname of the Containerlab host; defaults to localhost (you do not need to include this option if Containerlab is running locally)")
@click.option("--inputfile", "-i", required=True,
              help="Specify the path to the input JSON file containing node(s) for one or more labs")
@click.option("--outputfile", "-o", required=True,
              help="Specify the path to the output JSON file to which to write the output containing running node information in JSON format")
def parse_inspect_output(inputfile: str, outputfile: str, clabHost: str) -> None:
    """Process clab inspect output for details about running nodes"""
    try:
        data = read_object_from_structured_data(filename=inputfile, expected_format="json")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error while reading clab inspect output from {inputfile}: {e}")
        exit(-1)

    parsedOutput = {}
    for name, nodes in data.items():
        errorString = f"Error while processing lab {name} from the clab inspect output in {inputfile}"
        print(f"Parsing output for lab {name}...")
        try:
            parsedOutput[name] = [{"name": node["Labels"]["clab-node-longname"],
                                   "image": node["Image"],
                                   "kind": node["Labels"]["clab-node-kind"],
                                   "state": node["State"],
                                   "ipv4_address": node["NetworkSettings"]["IPv4addr"],
                                   "ipv6_address": node["NetworkSettings"]["IPv6addr"],
                                   "ports": {
                                       "ssh": 22
                                   },
                                   "method": None}
                                  for node in check_if_list(data=nodes, errorString=errorString) if node["State"] == "running"]
        except (KeyError, TypeError) as e:
            handle_dict_access_errors(exception=e, errorString=errorString)

    write_output_to_file(outputfile=outputfile, data=write_common_metadata(host=clabHost, originalDict=parsedOutput))

@node_data.command()
@click.option("--datafile", "-d", required=True,
              help="Specify the path to the rendered JSON file containing running nodes that was generated by this utility using another node-data command")
@click.option("--portfile", "-p", required=True,
              help="Specify the path to the input YAML file containing the port numbers for nodes with custom/non-default port numbers")
@click.option("--output", "-o",
              help="Specify the output path for the new, rendered JSON file containing the custom ports for applicable running nodes; OPTIONAL, default is to replace the existing file. Only use this option if you care about keeping both the original and newly rendered JSON files")
def inject_custom_ports(output: str | None, portfile: str, datafile: str) -> None:
    """Customize port numbers for sessions to lab devices in rendered output

    REQUIRES rendered output generated by this utility using another node-data command"""
    try:
        data = read_object_from_structured_data(filename=datafile, expected_format="json")
        ports = read_object_from_structured_data(filename=portfile, expected_format="yaml")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error while reading rendered JSON file from {datafile}: {e}")
        exit(-1)
    except yaml.YAMLError as e:
        print(f"Error while reading YAML file containing ports from {datafile}: {e}")
        exit(-1)

    metadata = retrieve_and_delete_metadata(data=data, filename=datafile)

    try:
        nodeNames = {}
        for lab, nodes in data.items():
            nodeNames[lab] = [node["name"] for node in check_if_list(data=nodes, errorString=f"Error while processing lab {lab} from rendered JSON data")]
    except (KeyError, TypeError) as e:
        handle_dict_access_errors(exception=e, errorString=f"Error while processing nodes in lab {lab} from {datafile}")

    for lab, nodes in ports.items():
        if not isinstance(nodes, dict):
            print(f"Error while processing lab {lab} from rendered JSON data: nodes not contained in a proper YAML mapping")
            exit(-1)

        try:
            for name, ports in nodes.items():
                print(f"Changing SSH port number for node {name} to {ports['ssh']}...")
                data[lab][nodeNames[lab].index(name)]["ports"]["ssh"] = ports["ssh"]
                data[lab][nodeNames[lab].index(name)]["method"] = "clabHost"
        except (KeyError, TypeError) as e:
            handle_dict_access_errors(exception=e, errorString=f"Error while processing nodes in lab {lab} from {portfile}")
            exit(-1)


    fileName = output if output is not None else datafile
    print(f"Writing output with custom port numbers to {fileName}...")
    write_output_to_file(outputfile=fileName, data=({"_metadata_": metadata} | data))
