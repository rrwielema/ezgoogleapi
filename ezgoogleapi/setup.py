from setuptools import setup, find_packages

import pathlib

here = pathlib.Path(__file__).parent.resolve()

setup(
    name='ezgoogleapi',
    version='0.0.1',
    description="Easy to use Google API connector package",
    author='R.R. Wielema',
    author_email='rwielema+egpy@gmail.com',
    url='rrwielema',
    install_requires=[
        'google>=3.0.0',
        'google-api-python-client>=2.14.1',
        'pandas>=1.3.1'
    ]
)