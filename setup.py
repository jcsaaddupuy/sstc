#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = open("requirements.txt").read()

test_requirements = [
    # Nothing at the moment
]

setup(
    name='sstc',
    version='0.1.0',
    description="Simple torrent client on top of libtorrent rasterbar",
    long_description=readme + '\n\n' + history,
    author="Jean-Christophe Saad-Dupuy",
    author_email='jc.saaddupuy@fsfe.org',
    url='https://github.com/jcsaaddupuy/sstc',
    packages=[
        'sstc',
    ],
    package_dir={'sstc':
                 'sstc'},
    include_package_data=True,
    install_requires=requirements,
    license="WTFPL",
    zip_safe=False,
    keywords='sstc',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
