import argparse
import tomlkit
import typing as t
from pathlib import Path
from datetime import datetime


class ArgNamespace(argparse.Namespace):
    command: t.Literal["init", "build"]
    path: str
    output: str
    sort_by: t.Literal["mtime", "name", "size"]


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
            init.add_argument(
                "-S",
                "--sort_by",
                dest="sort_by",
                type=str,
                help="How to auto-sort the files. Either 'mtime', 'size' or 'name'",
                default="name",
            )
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
    print(args)
    path = Path(args.path).resolve()
    outpath = path / "sb2git.toml"
    if not path.exists():
        raise ValueError(f"{path} does not exist")

    def sortfunc(f: Path):
        match args.sort_by:
            case "mtime":
                return f.stat().st_mtime
            case "name":
                return f.name.lower()
            case "size":
                return f.stat().st_size
            case _:
                raise ValueError(f"Bad sort method {args.sort_by!r}")

    if outpath.exists():
        if input("Replace existing sb2git.toml? (y/N): ") != "y":
            return

    print(f"Walking {args.path}")
    files = list(path.iterdir())
    files.sort(key=sortfunc)

    file_arr = tomlkit.aot()
    for file in files:
        if not (file.name.endswith(".sb3") or file.name.endswith(".sprite3")):
            continue

        table = tomlkit.table()
        table.add("name", file.name.removesuffix(".sb3"))
        table.add("mtime", datetime.fromtimestamp(file.stat().st_mtime))
        table.add("ctime", datetime.fromtimestamp(file.stat().st_birthtime))
        table.add("size", file.stat().st_size)
        file_arr.append(table)

    content = {"files": file_arr}
    with outpath.open("w") as f:
        tomlkit.dump(content, f)


def build(args: ArgNamespace): ...
