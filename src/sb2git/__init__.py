import argparse
import shutil
from git import index
import tomlkit
import tomllib
import dataclasses
import zipfile
import json
import typing as t
import git
import scratchattach.editor  # this is slow but easier
from pathlib import Path
from slugify import slugify
from datetime import datetime, timezone


@dataclasses.dataclass
class Asset:
    md5: str = ""
    names: set[str] = dataclasses.field(default_factory=set)
    ext: str = ""
    content_written: bool = False
    # content: bytes = dataclasses.field(default=b"", repr=False)


class ArgNamespace(argparse.Namespace):
    command: t.Literal["init", "build"]
    path: str
    output: str
    sort_by: t.Literal["mtime", "name", "size"]
    author: str
    email: str


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
            build.add_argument("path", nargs="?", default=".", type=str)
            build.add_argument(
                "--author", type=str, help="name for git author", required=True
            )
            build.add_argument(
                "--email", type=str, help="email for git author", required=True
            )
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
            build(args)


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
            ending = file.name.split('.')[-1]
            if ending == "sb3":
                body = scratchattach.editor.Project.from_json(
                    json.loads(archive.read("project.json"))
                )  # using from json so assets aren't loaded and no extra zipfiling
            else:
                assert ending == "sprite3"
                body = scratchattach.editor.Sprite.from_json(
                    json.loads(archive.read("sprite.json"))
                )
            for file in archive.filelist:
                if file.filename.endswith(".json"):
                    continue
                asset = assets.get(file.filename, Asset())
                asset.ext = file.filename.split(".")[-1]
                asset.md5 = file.filename.removesuffix(f".{asset.ext}")

                for aobj in body.assets:
                    if aobj.file_name == file.filename:
                        asset.names.add(aobj.name)

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
        table.add("names", list(asset.names))
        table.add(
            "chosen_name", slugify(next(iter(asset.names))) if asset.names else "foo"
        )

        asset_arr.append(table)

    # store file toml
    file_arr = tomlkit.aot()
    for file in files:
        table = tomlkit.table()

        ext = file.name.split('.')[-1]
        table.add("name", file.name.removesuffix('.' + ext))
        table.add("ext", ext)
        table.add("mtime", datetime.fromtimestamp(file.stat().st_mtime))
        table.add("ctime", datetime.fromtimestamp(file.stat().st_birthtime))
        table.add("size", file.stat().st_size)

        file_arr.append(table)

    content = {"files": file_arr, "assets": asset_arr}
    with outpath.open("w", encoding="utf-8") as f:
        tomlkit.dump(content, f)


def build(args: ArgNamespace):
    # setup filesystem
    path = Path(args.path)
    config = path / "sb2git.toml"
    assets_in = path / "assets"
    assert path.exists() and path.is_dir()
    assert assets_in.exists() and assets_in.is_dir()

    output = path / args.output
    print(f"Building into {output}")

    if output.exists():
        if input(f"Overwrite {output}? (y/N): ") != "y":
            return
        shutil.rmtree(output)
    output.mkdir()

    assets_out = output / "assets"
    assets_out.mkdir()

    repo = git.Repo.init(output)
    actor = git.Actor(args.author, args.email)
    # load stuff
    data = tomllib.load(config.open("rb"))

    # put stuff in the repo
    # assets
    for asset in data["assets"]:
        fn: str = asset["md5"] + "." + asset["ext"]
        fp = assets_in / fn
        (assets_out / f"{asset["chosen_name"]}.{asset["ext"]}").write_bytes(fp.read_bytes())

    repo.index.add(["assets"])
    repo.index.commit("chore: add assets", author=actor)

    (output / "sb2git.toml").write_bytes(config.read_bytes())
    repo.index.add(["sb2git.toml"])
    repo.index.commit("chore: add original config", author=actor)

    # add proj json in order
    for file in data["files"]:
        name: str = file["name"]
        fp = path / (name + "." + file["ext"])
        (output / "project.json").unlink(missing_ok=True)
        (output / "sprite.json").unlink(missing_ok=True)

        if file["ext"] == "sb3":
            with zipfile.ZipFile(fp) as archive:
                content = archive.read("project.json")
                (output / "project.json").write_text(json.dumps(json.loads(content), indent=3))
        else:
            with zipfile.ZipFile(fp) as archive:
                content = archive.read("sprite.json")
                (output / "sprite.json").write_text(json.dumps(json.loads(content), indent=3))
        
        tomlkit.dump({
            **file
        }, (output / "instance.toml").open("w", encoding="utf-8"))
        repo.index.add(["."])
        mod_at: datetime = file["mtime"]
        mod_at = datetime(
            mod_at.year,
            mod_at.month, 
            mod_at.day, 
            mod_at.hour, 
            mod_at.minute, 
            mod_at.second, 
            mod_at.microsecond, 
            timezone.utc
        )
        repo.index.commit(f"feat: {file["name"]}", author=actor, author_date=mod_at)
        print(f"committed {file}")

    print(repo)
