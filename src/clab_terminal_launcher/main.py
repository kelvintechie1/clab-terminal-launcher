import click

from .node_data.commands import node_data
from .launch.commands import launch

@click.group()
def main():
    """Containerlab (clab) Terminal Launcher -- A solution to take the hassle out of
    launching sessions and connecting to virtualized network devices running in Containerlab"""
    pass

main.add_command(node_data)
main.add_command(launch)

if __name__ == "__main__":
    main()