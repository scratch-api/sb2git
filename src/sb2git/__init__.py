import argparse
import typing as t
from pathlib import Path
from datetime import datetime


class ArgNamespace(argparse.Namespace):
    command: t.Literal["init", "build"]
    path: str
    output: str


def main() -> None:
    parser = argparse.ArgumentParser(
        "sb2git",
        "`sb2git .`",
        "Converter from sb3 directory to git repo",
        "gh: https://github.com/scratch-api/sb2git",
    )

    if command := parser.add_subparsers(dest="command", required=True):
        if init := command.add_parser("init", help="Set up a sb2git.toml file"):
            init.add_argument("path", nargs="?", default=".", type=str)
        if build := command.add_parser(
            "build", help="Build a sb2git input directory into an output directory"
        ):
            build.add_argument(
                "-o", "--output", type=str, default="build", help="Output directory"
            )
    args = parser.parse_args(namespace=ArgNamespace())
    run(args)


def run(args: ArgNamespace):
    match args.command:
        case "init":
            init(args)
        case "build":
            ...


def init(args: ArgNamespace):
    path = Path(args.path).resolve()
    if not path.exists():
        raise ValueError(f"{path} does not exist")

    print(f"Walking {args.path}")
    for file in path.iterdir():
        created_at = datetime.fromtimestamp(file.stat().st_mtime)
        print(file, created_at)


def build(args: ArgNamespace): ...
