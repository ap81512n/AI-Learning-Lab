
from argparse import ArgumentParser
from rich.console import Console


def build_status(
    client: str,
    environment: str = "development"
) -> str:
    return (
        f"READY | client={client} "
        f"| environment={environment}"
    )


def main() -> None:
    parser = ArgumentParser(
        description="FDE customer environment diagnostic"
    )

    parser.add_argument("--client", required=True)

    parser.add_argument(
        "--environment",
        default="development",
        help="Target environment"
    )

    args = parser.parse_args()

    console = Console()
    console.print(
        f"[bold green]"
        f"{build_status(args.client, args.environment)}"
        f"[/bold green]"
    )
