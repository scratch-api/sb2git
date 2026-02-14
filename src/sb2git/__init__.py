import argparse
import shutil
import tomlkit
import dataclasses
import zipfile
import typing as t
from pathlib import Path
from datetime import datetime


@dataclasses.dataclass
class Asset:
    md5: str = ""
    # names: list[str] = dataclasses.field(default_factory=list)
    ext: str = ""
    content_written: bool = False
    # content: bytes = dataclasses.field(default=b"", repr=False)


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
    assetpath = path / "assets"
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

    if assetpath.exists():
        if input("Replace existing asset/ directory? (y/N): ") != "y":
            return
        shutil.rmtree(assetpath)
    if outpath.exists():
        if input("Replace existing sb2git.toml? (y/N): ") != "y":
            return

    print(f"Walking {args.path}")
    assetpath.mkdir()
    files = list(
        p
        for p in path.iterdir()
        if p.name.endswith(".sb3") or p.name.endswith(".sprite3")
    )
    files.sort(key=sortfunc)
    # store asset toml
    assets: dict[str, Asset] = {}
    for file in files:
        with zipfile.ZipFile(file) as archive:
            for file in archive.filelist:
                if file.filename.endswith(".json"):
                    continue
                asset = assets.get(file.filename, Asset())
                asset.ext = file.filename.split(".")[-1]
                asset.md5 = file.filename.removesuffix(f".{asset.ext}")
                # asset.names.append()  # TODO: read sprite.json or project.json

                if not asset.content_written:
                    (assetpath / file.filename).write_bytes(archive.read(file.filename))
                asset.content_written = True
                assets[file.filename] = asset

    asset_arr = tomlkit.aot()
    for asset in assets.values():
        table = tomlkit.table()

        print(asset)
        table.add("md5", asset.md5)
        table.add("ext", asset.ext)

        asset_arr.append(table)
    # store file toml
    file_arr = tomlkit.aot()
    for file in files:
        table = tomlkit.table()

        table.add("name", file.name.removesuffix(".sb3"))
        table.add("mtime", datetime.fromtimestamp(file.stat().st_mtime))
        table.add("ctime", datetime.fromtimestamp(file.stat().st_birthtime))
        table.add("size", file.stat().st_size)

        file_arr.append(table)

    content = {"files": file_arr, "assets": asset_arr}
    with outpath.open("w") as f:
        tomlkit.dump(content, f)


def build(args: ArgNamespace): ...
