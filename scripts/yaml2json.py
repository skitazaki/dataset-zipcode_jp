#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Convert datapackage file format from YAML to JSON.
"""

import json
import pathlib

import yaml

__version__ = '0.3.0'

SCRIPTPATH = pathlib.Path(__file__)
APPNAME = SCRIPTPATH.stem
BASEDIR = SCRIPTPATH.parent.parent.resolve()

DATAPACKAGE_NAME = 'datapackage.json'
DATAPACKAGE_FILE = BASEDIR.joinpath(DATAPACKAGE_NAME)

DATAPACKAGE_SOURCE_NAME = 'datapackage.yml'
DATAPACKAGE_SOURCE_FILE = BASEDIR.joinpath(DATAPACKAGE_SOURCE_NAME)


def main():
    """Driver function to dispatch the process."""
    source = yaml.load(DATAPACKAGE_SOURCE_FILE.open())
    output = DATAPACKAGE_FILE.open('w')
    json.dump(source, output, indent=2, sort_keys=True, ensure_ascii=False)


if __name__ == '__main__':
    main()

# vim: set et ts=4 sw=4 cindent fileencoding=utf-8 :
