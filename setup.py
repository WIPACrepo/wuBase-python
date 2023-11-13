from setuptools import setup

setup(
    name='pywub',
    version='2.1',
    packages=['pywub'],
    package_data={'pywub': ['wubase_commands.txt']},
    setup_requires=[
        'wheel',
        'coloredlogs>=15.0',
        'matplotlib>=3.7',
        'numpy>=1.24',
        'pyserial>=3.5'
        ]
)
