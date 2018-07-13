#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Pull Zip archive, extract CSV file, and convert encoding into UTF-8.
"""

import atexit
import codecs
import copy
import logging
import os
import json
import shutil
import tempfile
import unicodedata
import zipfile
from functools import partial

try:  # Python 2.x
    from urllib import urlretrieve
except ImportError:  # Python 3.x
    from urllib.request import urlretrieve

APPNAME = os.path.splitext(os.path.basename(__file__))[0]
VERSION = '0.2.0'

LOG_FORMAT = '%(asctime)s|%(levelname)s|%(message)s'
LOG_FORMAT_DEBUG = '%(asctime)s | %(name)s:%(levelname)s | ' + \
                   '%(filename)s:%(lineno)d | %(message)s'
LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'

ORIGINAL_ENCODING = 'cp932'  # Downloaded file encoding
ENCODING = 'utf-8'  # Follow "Open Data Protocol"
NORMALIZATION_FORM = 'NFKC'
BASEDIR = os.path.join(os.path.dirname(__file__), '..')
DATA_DIR = os.path.join(BASEDIR, 'data')
DATA_PACKAGE = os.path.join(BASEDIR, 'datapackage.json')

REMOTE_DIR = "https://www.post.japanpost.jp/zipcode/dl"
RESOURCES = (
    {
        "name": "ken_all_oogaki",
        "url": REMOTE_DIR + "/oogaki/zip/ken_all.zip"
    },
    {
        "name": "ken_all_kogaki",
        "url": REMOTE_DIR + "/kogaki/zip/ken_all.zip"
    },
    {
        "name": "ken_all_roman",
        "url": REMOTE_DIR + "/roman/ken_all_rome.zip"
    },
    {
        "name": "facility",
        "url": REMOTE_DIR + "/jigyosyo/zip/jigyosyo.zip"
    }
)


class Event(object):

    callbacks = []
    errbacks = []

    def callback(self, callback):
        self.callbacks.append(callback)

    def errback(self, errback):
        self.errbacks.append(errback)

    def fire(self, resource):
        r = resource
        for callback in self.callbacks:
            try:
                r = callback(r)
                if r is None:
                    return
            except Exception as e:
                for errback in self.errbacks:
                    errback(e)
                return


class ZipDownloadUnpack(object):

    def __init__(self, basedir):
        self.basedir = basedir
        self.logger = logging.getLogger(APPNAME)
        self.cachedir = tempfile.mkdtemp()
        atexit.register(shutil.rmtree, self.cachedir)
        self.logger.debug('Created cache directory: %s', self.cachedir)

    def process(self, resource):
        self.logger.info('Start processing: %s', resource['name'])
        evt = Event()
        evt.callback(self.download)
        evt.callback(self.unpack)
        evt.callback(self.convert)
        evt.callback(self.write)
        evt.errback(self.logger.error)
        evt.fire(resource)
        self.logger.info('End processing: %s', resource['name'])

    def download(self, resource):
        path = os.path.join(self.cachedir, resource['name'] + '.zip')
        if os.path.exists(path):
            self.logger.debug('"%s" is already downloaded.', resource['name'])
            return
        self.logger.info('Start downloading: %s -> %s', resource['url'], path)
        urlretrieve(resource['url'], path)
        self.logger.info('Successfully downloaded "{}" {:,} bytes.'.format(
            os.path.basename(path), os.path.getsize(path)))
        return resource

    def unpack(self, resource):
        path = os.path.join(self.cachedir, resource['name'] + '.zip')
        self.logger.debug('Unpacking ZIP file: %s', path)
        with zipfile.ZipFile(path) as z:
            for f in z.namelist():
                if f.lower().endswith('.csv'):
                    z.extract(f, self.cachedir)
                    resource['_local'] = os.path.join(self.cachedir, f)
                    return resource

    def convert(self, resource):
        # Convert half-width Katakana to full-width
        path = resource['_local']
        self.logger.debug('Converting CSV file: %s', path)
        data = []
        normalize = partial(unicodedata.normalize, NORMALIZATION_FORM)
        with codecs.open(path, 'r', ORIGINAL_ENCODING) as fp:
            for line in fp:
                data.append(normalize(line.rstrip('\r\n')))
        resource['data'] = data
        return resource

    def write(self, resource):
        path = os.path.join(self.basedir, resource['path'])
        encoding = resource.get('encoding', ENCODING)
        fields = resource['schema']['fields']
        data = resource['data']
        with codecs.open(path, 'w', encoding) as w:
            header = tuple(map(lambda f: f['name'], fields))
            w.write(','.join(header))
            w.write('\n')
            w.write('\n'.join(data))
            w.write('\n')
        self.logger.info('Wrote "{}" {:,} bytes of {:,} lines.'.format(
            resource['path'], os.path.getsize(path), len(data)))


def setup_logger(verbosity=logging.INFO):
    logger = logging.getLogger(APPNAME)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(verbosity)
    fmt = LOG_FORMAT_DEBUG if verbosity == logging.DEBUG else LOG_FORMAT
    handler.setFormatter(logging.Formatter(fmt, datefmt=LOG_DATEFMT))
    logger.addHandler(handler)
    return logger


def main():
    logger = setup_logger()
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    with open(DATA_PACKAGE) as fp:
        package = json.load(fp)
    resources = package['resources']
    processor = ZipDownloadUnpack(BASEDIR)
    for r in RESOURCES:
        s = tuple(filter(lambda t: t['name'] == r['name'], resources))
        if s:
            a = copy.copy(s[0])
            a['url'] = r['url']
            processor.process(a)
        else:
            logger.error('"%s" is not found on datapackage.', r['name'])


if __name__ == '__main__':
    main()

# vim: set et ts=4 sw=4 cindent fileencoding=utf-8 :
