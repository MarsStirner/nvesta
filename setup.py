#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='nvesta',
    version='0.2.4',
    url='https://stash.bars-open.ru/scm/medvtr/nvesta.git',
    author='hitsl',
    description='Reference Book subsystem',
    long_description='', # read('README.md'),
    include_package_data=True,
    packages=find_packages(),
    package_data={
        'nvesta': [
            'static/*',
            'templates/*',
        ],
        'nvesta.admin': [
            # 'static/*',
            'static/js/*',
            'static/partials/*',
            'templates/admin/*',
        ]
    },
    platforms='any',
    install_requires=[
        'Flask',
        'Flask-Fanstatic',
        'Flask-PyMongo',
        'Flask-Cache',
        'Requests',
        'js.bootstrap',
        'js.angular',
        'js.momentjs',
        'js.fontawesome',
        'js.ui_bootstrap',
        'js.underscore',
        'hitsl_utils',
        'zeep',
    ],
    entry_points={
        'console_scripts': {
            'vesta-update-nsi=nvesta.cli:update_nsi_dicts',
            'vesta-migrate-v1=nvesta.cli:migrate_from_v1',
            'vesta-kladr-maintenance=nvesta.cli:kladr_maintenance',
        }
    },
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
