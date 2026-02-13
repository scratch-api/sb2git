import argparse
import typing as t


class ArgNamespace(argparse.Namespace):
    path: str


def main() -> None:
    parser = argparse.ArgumentParser(
        "sb2git",
        "`sb2git .`",
        "Converter from sb3 directory to git repo",
        "gh: https://github.com/scratch-api/sb2git",
    )

    parser.add_argument("path", type=str)
    args = parser.parse_args(namespace=ArgNamespace())
    run(args)


def run(args: ArgNamespace):
    print(f"Hello from sb2git! {args}")
