import click
from dotenv import dotenv_values

from .helpers import validate_required_keys, parse_settings, run_command
from ..node_data.commands import retrieve_from_api, parse_inspect_output, inject_custom_ports
from ..launch.commands import SecureCRT, PuTTY, MTPuTTY, native_OpenSSH


@click.command()
@click.option("--config", "-c", default="config.env",
              help="Specify the path to the config file in plain text environment variable/Bash format (see docs for more details); default: config.env in the local directory")
@click.pass_context
def quick(ctx: click.Context, config: str) -> None:
    """Quickly perform all commands required to launch sessions to connect to lab devices,
    based on a configuration file"""

    # Import defined variables and validate that basic, required variables are present
    settings = dotenv_values(config)
    validate_required_keys(task="validating basic settings",
                           requiredKeys={"retrieval_method": "BASIC_RETRIEVAL_METHOD",
                                         "launch_method": "BASIC_LAUNCH_METHOD"},
                           settings=settings,
                           config=config)

    # Retrieve nodes based on retrieval method
    match settings["BASIC_RETRIEVAL_METHOD"].lower():
        case "api":
            requiredKeys = {"username": "RETRIEVE_API_USERNAME",
                            "outputfile": "RETRIEVE_API_OUTPUT"}
            optionalKeys = {"password": "RETRIEVE_API_PASSWORD",
                            "clabHost": "RETRIEVE_API_HOST",
                            "labs": "RETRIEVE_API_LABS"}
            task = "API"
            func = retrieve_from_api
        case "inspect":
            requiredKeys = {"inputfile": "RETRIEVE_INSPECT_INPUT",
                            "outputfile": "RETRIEVE_INSPECT_OUTPUT"}
            optionalKeys = {"clabHost": "RETRIEVE_INSPECT_HOST"}
            task = "inspect output parser"
            func = parse_inspect_output
        case _:
            print(f"Error, the retrieval method provided under the \"BASIC_RETRIEVAL_METHOD\" option ({settings['BASIC_RETRIEVAL_METHOD']}) is not valid")
            exit(-1)

    run_command(task=task, settings=settings, config=config, ctx=ctx, func=func, requiredKeys=requiredKeys, optionalKeys=optionalKeys)

    # Inject custom ports if a port file is provided
    if "RETRIEVE_PORTS_FILE" in settings:
        requiredKeys = {"portfile": "RETRIEVE_PORTS_FILE"}
        optionalKeys = {"output": "RETRIEVE_PORTS_OUTPUT"}
        ctx.invoke(inject_custom_ports, **(parse_settings(settings=settings,
                                                          searchKeys=(requiredKeys | optionalKeys)) | {"datafile": parse_settings(settings=settings,
                                                                                                                                  searchKeys=requiredKeys["outputfile"])["outputfile"]}))

    # Launch sessions to connect to lab devices in Containerlab, based on the provided launch method
    match settings["BASIC_LAUNCH_METHOD"].lower():
        case "securecrt":
            requiredKeys = {"creds": "LAUNCH_SECURECRT_CREDS",
                            "inputfile": "LAUNCH_SECURECRT_INPUT"}
            optionalKeys = {"method": "LAUNCH_SECURECRT_METHOD",
                            "jumphost": "LAUNCH_SECURECRT_JUMPHOST",
                            "executable": "LAUNCH_SECURECRT_EXECUTABLE"}
            func = SecureCRT
        case "putty":
            requiredKeys = {"creds": "LAUNCH_PUTTY_CREDS",
                            "inputfile": "LAUNCH_PUTTY_INPUT"}
            optionalKeys = {"method": "LAUNCH_PUTTY_METHOD",
                            "jumphost": "LAUNCH_PUTTY_JUMPHOST",
                            "executable": "LAUNCH_PUTTY_EXECUTABLE"}
            func = PuTTY
        case "mtputty":
            requiredKeys = {"creds": "LAUNCH_MTPUTTY_CREDS",
                            "inputfile": "LAUNCH_MTPUTTY_INPUT"}
            optionalKeys = {"method": "LAUNCH_MTPUTTY_METHOD",
                            "jumphost": "LAUNCH_MTPUTTY_JUMPHOST",
                            "config": "LAUNCH_MTPUTTY_CONFIG"}
            func = MTPuTTY
        case "native-openssh":
            requiredKeys = {"creds": "LAUNCH_OPENSSH_CREDS",
                            "inputfile": "LAUNCH_OPENSSH_INPUT",
                            "terminal": "LAUNCH_OPENSSH_TERMINAL"}
            optionalKeys = {"method": "LAUNCH_SECURECRT_METHOD",
                            "jumphost": "LAUNCH_SECURECRT_JUMPHOST",
                            "executable": "LAUNCH_SECURECRT_EXECUTABLE"}
            func = native_OpenSSH
        case _:
            print(f"Error, the launch method provided under the \"BASIC_LAUNCH_METHOD\" option ({settings['BASIC_LAUNCH_METHOD']}) is not valid")
            exit(-1)

    run_command(task=f"validating {func.__dict__["name"].replace('_', ' ')} settings", settings=settings, config=config,
                ctx=ctx, func=func, requiredKeys=requiredKeys, optionalKeys=optionalKeys)