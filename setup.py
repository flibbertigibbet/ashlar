#!/usr/bin/env python

from setuptools import setup, find_packages

tests_require = []

setup(
    name='ashlar',
    version='0.0.1',
    description='Define and validate schemas for metadata for geotemporal event records',
    author='Azavea, Inc.',
    author_email='info@azavea.com',
    keywords='gis jsonschema',
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'Django >=1.8',
        'djangorestframework >=3.1.1',
        'djangorestframework-gis >=0.8.1',
        'django-filter >=0.9.2',
        'jsonschema >=2.4.0',
        'django-pgjson >=0.2.3',
        'psycopg2 >=2.6',
        'django-extensions >=1.5.2',
        'PyYAML >=3.11'
    ],
    extras_require={
        'dev': [],
        'test': tests_require
    },
    test_suite='tests',
    tests_require=tests_require,
)