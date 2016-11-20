"""
elchHub Web interface
"""
from setuptools import setup

setup(
    name='elchHub',
    version='1.0.3',
    long_description=__doc__,
    packages=['elchhub'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'Flask',
        'requests>=2',
        'ftputil'
    ],
    entry_points = {
        'console_scripts': [
                'elch-manager = elchhub.elch_manager:main',
            ],
        },
    author_email="spam@krebsco.de",
    url="http://github.com/krebscode/elchhub"
)

