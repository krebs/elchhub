"""
elchHub Web interface
"""
from setuptools import setup

setup(
    name='elchHub',
    version='1.0',
    long_description=__doc__,
    packages=['elchhub'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'Flask',
        'ftplib',
        'requests>=2'
    ],
    url="http://github.com/krebscode/elchhub"
)

