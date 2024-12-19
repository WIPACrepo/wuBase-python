import sys
from setuptools import setup

# Additional dependencies for older python versions;
# see also STM32Tools setup.py:
if sys.version_info < (3, 8):
    extra_deps = [
        "numpy==1.21",
        "pytest==7.1.2",
        "setuptools_scm==6.3.2",
    ]
elif sys.version_info[:2] == (3, 8):
    extra_deps = [
        "numpy==1.24",
        "pytest==7.3.1",
        "setuptools_scm==6.3.2",
    ]
else:
    # Use newer Numpy:
    extra_deps = ["numpy", "pytest==7.3.1"]

setup(
    name="pywub",
    version="3.1",
    packages=["pywub"],
    package_data={"pywub": ["wubase_commands.txt"]},
    install_requires=["wheel", "numpy", "pyserial"] + extra_deps,
)
