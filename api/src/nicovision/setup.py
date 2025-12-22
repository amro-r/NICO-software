#!/usr/bin/env python
from setuptools import find_packages, setup

setup(
    name="nicovision",
    version="1.0",
    packages=find_packages("scripts/"),
    package_dir={"": "scripts"},
    description="NICO api package for vision related modules",
    author="Connor Gaede",
    author_email="4gaede@informatik.uni-hamburg.de",
    install_requires=[
        "numpy",
        # FIXME remove version when qt incompatibility fixed
        "opencv-python==4.3.0.36",
    ],
)
