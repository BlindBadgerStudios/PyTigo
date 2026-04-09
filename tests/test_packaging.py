from pathlib import Path

import tomllib

from pytigo import __version__


def test_version_exported():
    assert __version__ == "0.4.3"


def test_pyproject_has_official_api_positioning():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    project = pyproject["project"]
    assert project["name"] == "pytigo"
    assert project["license"] == "MIT"
    assert "authors" in project and project["authors"]
    assert any(dep.startswith("requests") for dep in project["dependencies"])
    assert "build" in project["optional-dependencies"]["dev"]
    assert "twine" in project["optional-dependencies"]["dev"]


def test_manifest_and_readme_files_exist():
    assert Path("README.md").exists()
    assert Path("LICENSE").exists()
    assert Path("MANIFEST.in").exists()
