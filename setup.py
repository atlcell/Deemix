#!/usr/env/bin python3
import pathlib
from setuptools import setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name="deemix",
    version="1.0.0",
    description="A barebone deezer downloader library",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://notabug.org/RemixDev/deemix",
    author="RemixDev",
    author_email="RemixDev64@gmail.com",
    license="GPL3",
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=["click", "pycryptodomex", "mutagen", "requests", "spotipy"],
    entry_points={
        "console_scripts": [
            "deemix=reader.__main__:main",
        ]
    },
)
