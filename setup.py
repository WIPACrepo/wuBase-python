from setuptools import setup

setup(
    name="pywub",
    version="3.1",
    packages=["pywub"],
    package_data={"pywub": ["wubase_commands.txt"]},
    install_requires=["wheel", "numpy", "pyserial"],
)
