#!/usr/bin/env python3
"""
Setup script for pg-mirror.
For modern Python packaging, prefer pyproject.toml, but setup.py is kept for compatibility.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read version from pyproject.toml to keep single source of truth
version = "1.0.0"
try:
    import tomli
    with open("pyproject.toml", "rb") as f:
        pyproject = tomli.load(f)
        version = pyproject.get("tool", {}).get("poetry", {}).get("version", "1.0.0")
except Exception:
    # Fallback to default version if tomli is not available
    pass

setup(
    name="pg-mirror",
    version=version,
    author="Davi Silva Rafacho",
    author_email="rafacho@zettabyte.tech",
    description="High-performance PostgreSQL database mirroring tool with parallel processing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/davisilvarafacho/pg-mirror",
    project_urls={
        "Bug Tracker": "https://github.com/davisilvarafacho/pg-mirror/issues",
        "Documentation": "https://github.com/davisilvarafacho/pg-mirror#readme",
        "Source Code": "https://github.com/davisilvarafacho/pg-mirror",
        "Changelog": "https://github.com/davisilvarafacho/pg-mirror/blob/main/CHANGELOG.md",
    },
    packages=find_packages(exclude=["tests", "tests.*", "docs", "examples"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Database",
        "Topic :: System :: Archiving :: Backup",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Environment :: Console",
        "Natural Language :: Portuguese (Brazilian)",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.4.2",
            "pytest-cov>=7.0.0",
            "pytest-mock>=3.11.1",
            "black>=23.7.0",
            "ruff>=0.0.285",
            "mypy>=1.5.0",
        ],
        "test": [
            "pytest>=8.4.2",
            "pytest-cov>=7.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pg-mirror=pg_mirror.cli:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "postgresql",
        "postgres",
        "database",
        "backup",
        "restore",
        "migration",
        "mirror",
        "replication",
        "pg_dump",
        "pg_restore",
        "cli",
        "devops",
        "sysadmin",
    ],
    platforms=["any"],
)
