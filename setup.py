import sys
from setuptools import setup

if sys.version_info < (3, 8):
    extra_deps = ["numpy==1.21"]
elif sys.version_info[:2] == (3, 8):
    extra_deps = ["numpy==1.24"]
else:
    # Use newer Numpy:
    extra_deps = ["numpy==1.26.1"]

setup(
    name="pywub",
    version="2.1",
    packages=["pywub"],
    package_data={"pywub": ["wubase_commands.txt"]},
    install_requires=["wheel",
                      "coloredlogs>=15.0",
                      "matplotlib",
                      "numpy",
                      "pyserial"]
    + extra_deps,
)
