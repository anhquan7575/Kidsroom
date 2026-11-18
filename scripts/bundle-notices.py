from importlib.metadata import distribution
import json
from pathlib import Path
import shutil
import sys


root = Path(__file__).resolve().parent.parent
destination = Path(sys.argv[1]).resolve() / "licenses"
destination.mkdir(parents=True, exist_ok=True)
projects = [
    "PySide6-Essentials", "shiboken6", "numpy", "opencv-python-headless",
    "mss", "pywin32", "pyinstaller",
]
versions = {"Python": sys.version.split()[0]}
for project in projects:
    package = distribution(project)
    if package.files is None:
        raise RuntimeError(f"No installed file manifest for {project}.")
    versions[project] = package.version
    for relative in package.files:
        if ".dist-info/licenses/" not in str(relative).casefold() and not relative.name.casefold().startswith(
            ("license", "copying", "copyright", "notice")
        ):
            continue
        target = (destination / project / relative).resolve()
        if not target.is_relative_to(destination):
            raise ValueError(f"License destination escapes bundle: {relative}")
        source = Path(package.locate_file(relative))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", destination / "Python-LICENSE.txt")
for name in ("LGPL-3.0.txt", "GPL-3.0.txt"):
    shutil.copyfile(root / "packaging" / "licenses" / name, destination / name)
shutil.copyfile(root / "packaging" / "THIRD-PARTY-NOTICES.txt",
                destination.parent / "THIRD-PARTY-NOTICES.txt")
(destination / "VERSIONS.json").write_text(json.dumps(versions, indent=2), encoding="utf-8")
