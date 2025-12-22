#!/usr/bin/env python
from setuptools import find_packages, setup

setup(
    name="nicomotion",
    version="1.0",
    packages=find_packages("scripts/"),
    package_dir={"": "scripts"},
    package_data={"": ["scripts/nicomotion/urdf/*"]},
    include_package_data=True,
    description="NICO api package for motion related modules",
    author="Connor Gaede",
    author_email="4gaede@informatik.uni-hamburg.de",
    install_requires=["math3d", "transforms3d", "numpy", "matplotlib", "gaikpy",],
)
