from setuptools import setup, find_packages
import sys, os

version = "0.1"

setup(
    name="routr",
    version=version,
    description="URL routing made right",
    author="Andrey Popp",
    author_email="8mayday@gmail.com",
    license="BSD",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    include_package_data=True,
    test_suite="routr.tests",
    zip_safe=False)
