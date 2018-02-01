#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Generate CREATE statement from datapackage.json
'''

import datetime
import logging
import logging.config
import pathlib
import sys

from datapackage import Package
from jinja2 import Template

__version__ = '0.2.0'

SCRIPTPATH = pathlib.Path(__file__)
APPNAME = SCRIPTPATH.stem
BASEDIR = SCRIPTPATH.parent.parent.resolve()

LOGGINGCONFIG_NAME = 'logging.yml'
LOGGINGCONFIG_FILE = SCRIPTPATH.parent.joinpath(LOGGINGCONFIG_NAME)

DATAPACKAGE_NAME = 'datapackage.json'
DATAPACKAGE_FILE = BASEDIR.joinpath(DATAPACKAGE_NAME)

TEMPLATE_SQL_HEADER = '''
--
-- Auto generated at {{ now.strftime('%Y/%m/%d %H:%M:%S') }}
--
-- Resources:
{% for table in tables %}--   * {{ table }}
{% endfor %}
'''.strip()

TEMPLATE_SQL_CREATE = '''
-- DROP TABLE IF EXISTS {{ name }} ;

CREATE TABLE IF NOT EXISTS {{ name }} (
{% for field in fields %}  "{{ field.name }}"{{ ' ' }}
  {%- if field.type == 'string' -%}
    {%- if field.constraints.get('maxLength') %}
      {%- if field.constraints.get('minLength') and field.constraints.get('minLength') == field.constraints.get('maxLength') %}
        CHAR({{ field.constraints.get('minLength') }})
      {%- else -%}
        VARCHAR({{ field.constraints.get('maxLength') }})
      {% endif -%}
    {%- else -%}VARCHAR(100)
    {%- endif -%}
  {%- elif field.type == 'integer' %}INTEGER
  {%- elif field.type == 'boolean' %}BOOLEAN
  {%- endif -%}
  {%- if field.required %} NOT NULL{% endif -%}
  {%- if loop.nextitem is defined %},{% endif -%}
  {%- if field.descriptor.get('title') %} -- {{ field.descriptor.get('title') }} {%- endif %}
{% endfor -%}
) ;

{% if path -%}
-- \COPY {{ name }} FROM '{{ path }}' WITH ( FORMAT CSV, HEADER TRUE, NULL '' )
{%- endif %}
'''

if LOGGINGCONFIG_FILE.exists():
    import yaml
    cfg = yaml.load(LOGGINGCONFIG_FILE.open())
    logging.config.dictConfig(cfg)


def main():
    p = Package(str(DATAPACKAGE_FILE))
    logger = logging.getLogger(APPNAME)
    logger.info('load datapackage file: %s', DATAPACKAGE_FILE)
    logger.info('package has %d resources', len(p.resources))
    template = Template(TEMPLATE_SQL_CREATE)
    writer = sys.stdout
    writer.write(Template(TEMPLATE_SQL_HEADER).render(
        now=datetime.datetime.now(),
        tables=p.resource_names
    ))
    for r in p.resources:
        s = r.schema
        logger.info('%s has %s fields', r.name, len(s.fields))
        path = None
        if r.local:
            path = r.source
        writer.write(template.render(name=r.name, fields=s.fields, path=path))
        writer.write('\n')


if __name__ == '__main__':
    main()

# vim: set et ts=4 sw=4 cindent fileencoding=utf-8 :
