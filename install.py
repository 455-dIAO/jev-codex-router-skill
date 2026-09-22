"""Install this distribution's Skill without modifying Codex config or Hooks."""
import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

NAME = "jev-codex-router"
FILES = (
    "SKILL.md", "agents/openai.yaml", "scripts/route.py",
    "references/configuration.md", "references/upstream-macos.md",
    "references/sources.md", "assets/task.example.json", "assets/router.example.json",
)


def linked(path):
    if path.is_symlink():
        return True
    if not path.exists():
        return False
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def install(skills_dir):
    source = Path(__file__).resolve().parent / NAME
    root = Path(skills_dir).expanduser().absolute()
    target = root / NAME
    for path in (root, *root.parents, target):
        if linked(path):
            raise ValueError("Refusing installation through a symlink or junction")
    if target.resolve() == source.resolve() or source.resolve() in target.resolve().parents or target.resolve() in source.resolve().parents:
        raise ValueError("Source and destination overlap")
    expected = {}
    for name in FILES:
        path = source / name
        if not path.is_file() or any(linked(p) for p in (path, *path.parents)):
            raise ValueError("Missing or linked distribution file")
        expected[name] = path.read_bytes()
    if target.exists():
        if any(linked(p) for p in target.rglob("*")):
            raise ValueError("Refusing linked destination contents")
        actual = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
        if actual == set(FILES) and all(not (target / n).is_symlink() and (target / n).read_bytes() == b for n, b in expected.items()):
            return {"status": "already_installed", "path": str(target)}
        raise ValueError("Destination differs; preserve it and choose another --skills-dir or manually back it up first")
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".jev-install-", dir=root) as temporary:
        staging = Path(temporary) / NAME
        staging.mkdir()
        for name, content in expected.items():
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            if path.read_bytes() != content:
                raise ValueError("Copy verification failed")
        staging.rename(target)
    return {"status": "installed", "path": str(target), "files": len(FILES)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"
    parser.add_argument("--skills-dir", type=Path, default=default)
    args = parser.parse_args()
    try:
        result = install(args.skills_dir)
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, ensure_ascii=True))
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
