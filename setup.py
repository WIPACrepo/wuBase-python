from setuptools import setup

setup(
    name='pywub',
    version='2.1',
    packages=['pywub'],
    package_data={'pywub': ['wubase_commands.txt']},
    install_requires=[
        'wheel',
        'coloredlogs>=15.0',
        'matplotlib',
        'numpy',
        'pyserial'
        ]
)
