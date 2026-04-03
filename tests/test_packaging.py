from pathlib import Path

import tomllib

from pytigo import __version__


def test_version_exported():
    assert __version__
    assert isinstance(__version__, str)


def test_pyproject_has_pypi_ready_metadata():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    project = pyproject["project"]

    assert project["name"] == "pytigo"
    assert project["license"] == "MIT"
    assert "authors" in project and project["authors"]
    assert "classifiers" in project and project["classifiers"]
    assert "License :: OSI Approved :: MIT License" not in project["classifiers"]
    assert "keywords" in project and project["keywords"]
    assert "Homepage" in project["urls"]
    assert any(dep.startswith("requests") for dep in project["dependencies"])
    assert "build" in project["optional-dependencies"]["dev"]
    assert "twine" in project["optional-dependencies"]["dev"]


def test_manifest_and_readme_files_exist():
    assert Path("README.md").exists()
    assert Path("LICENSE").exists()
