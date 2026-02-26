import click

from src.running_nodes import retrieve_running_nodes, parse_inspect_output
from src.launcher import launch

@click.group()
def main():
    pass

main.add_command(retrieve_running_nodes)
main.add_command(parse_inspect_output)
main.add_command(launch)

if __name__ == "__main__":
    main()