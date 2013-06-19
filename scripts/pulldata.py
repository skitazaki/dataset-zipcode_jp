#!/usr/bin/env python

"""Pull Zip archive, extract CSV file, and convert encoding into UTF-8.
"""

import atexit
import codecs
import logging
import os
import json
import shutil
import tempfile
import urllib
import zipfile

ORIGINAL_ENCODING = 'cp932'  # Downloaded file encoding
ENCODING = 'utf-8'  # Follow "Open Data Protocol"
BASEDIR = os.path.join(os.path.dirname(__file__), '..')
DATA_DIR = os.path.join(BASEDIR, 'data')
DATA_PACKAGE = os.path.join(BASEDIR, 'datapackage.json')

RESOURCES = (
    {
        "title": "Zip package (Oogaki)",
        "name": "ken_all_oogaki",
        "path": "data/ken_all_oogaki.csv",
        "url": "http://www.post.japanpost.jp/zipcode/dl/oogaki/zip/ken_all.zip"
    },
    {
        "title": "Zip package (Kogaki)",
        "name": "ken_all_kogaki",
        "path": "data/ken_all_kogaki.csv",
        "url": "http://www.post.japanpost.jp/zipcode/dl/kogaki/zip/ken_all.zip"
    },
    {
        "title": "Zip package (Roman)",
        "name": "ken_all_roman",
        "path": "data/ken_all_roman.csv",
        "url": "http://www.post.japanpost.jp/zipcode/dl/roman/ken_all_rome.zip"
    },
    {
        "title": "Zip package (Facility)",
        "name": "facility",
        "path": "data/facility.csv",
        "url": "http://www.post.japanpost.jp/zipcode/dl/jigyosyo/zip/jigyosyo.zip"
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
            except Exception, e:
                for errback in self.errbacks:
                    errback(e)
                return


class ZipDownloadUnpack(object):

    def __init__(self, datadir, cachedir):
        self.datadir = datadir
        self.cachedir = cachedir

    def process(self, resource, fields):
        logging.info('Start processing: %s', resource['name'])
        evt = Event()
        evt.callback(self.download)
        evt.callback(self.unpack)
        self.target = os.path.join(self.datadir, resource['name'] + '.csv')
        self.fields = fields
        evt.callback(self.write_header)
        evt.callback(self.convert)
        evt.errback(logging.error)
        evt.fire(resource)
        logging.info('End processing: %s', resource['name'])

    def download(self, resource):
        path = os.path.join(self.cachedir, resource['name'] + '.zip')
        if os.path.exists(path):
            logging.debug('%s already exists.', resource['name'])
            return
        try:
            urllib.urlretrieve(resource['url'], path)
        except IOError:
            logging.error('Fail to download from: %s', resource['url'])
        else:
            logging.info('Successfully downloaded: %s', resource['url'])
            return path

    def unpack(self, zipname):
        with zipfile.ZipFile(zipname) as z:
            for f in z.namelist():
                if f.endswith(('.csv', '.CSV')):
                    z.extract(f, self.cachedir)
                    return os.path.join(self.cachedir, f)

    def write_header(self, csvname):
        with codecs.open(self.target, 'w', ENCODING) as w:
            w.write(','.join(tuple(map(lambda f: f['id'], self.fields))))
            w.write('\n')
        return csvname

    def convert(self, csvname):
        with codecs.open(csvname, 'r', ORIGINAL_ENCODING) as r:
            with codecs.open(self.target, 'a', ENCODING) as w:
                [w.write(row) for row in r]


def main():
    cache = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, cache)
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    with open(DATA_PACKAGE) as fp:
        package = json.load(fp)
    resources = package['resources']
    processor = ZipDownloadUnpack(DATA_DIR, cache)
    for r in RESOURCES:
        s = filter(lambda t: t['path'] == r['path'], resources)
        if not s:
            logging.error('"%s" is not found on datapackage to compare path attribute.', r['title'])
            continue
        processor.process(r, s[0]['schema']['fields'])


if __name__ == '__main__':
    main()

# vim: set et ts=4 sw=4 cindent fileencoding=utf-8 :
