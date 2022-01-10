# -*- coding: utf-8 -*-

"""Lambda handler to refresh a data package.
"""

import asyncio
import datetime
import hashlib
import json
import logging
import os
import shutil
import tempfile
import urllib.request
import unicodedata
import zipfile
from functools import partial
from typing import Optional

import boto3

DATA_SOURCE_BASE_URL = "https://www.post.japanpost.jp/zipcode/dl"
DATA_SOURCES = (
    {
        "name": "ken_all_oogaki",
        "url": DATA_SOURCE_BASE_URL + "/oogaki/zip/ken_all.zip"
    },
    {
        "name": "ken_all_kogaki",
        "url": DATA_SOURCE_BASE_URL + "/kogaki/zip/ken_all.zip"
    },
    {
        "name": "ken_all_roman",
        "url": DATA_SOURCE_BASE_URL + "/roman/ken_all_rome.zip"
    },
    {
        "name": "facility",
        "url": DATA_SOURCE_BASE_URL + "/jigyosyo/zip/jigyosyo.zip"
    }
)

DATA_SOURCE_ENCODING = 'cp932'
DATA_PACKAGE_ENCODING = 'utf-8'
DATA_PACKAGE_NORMALIZATION_FORM = 'NFKC'

BASE_DIR = os.path.dirname(__file__)
DATA_PACKAGE = os.path.join(BASE_DIR, 'datapackage.json')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

with open(DATA_PACKAGE, encoding='utf8') as fp:
    package = json.load(fp)
resources = package['resources']
logger.info('the target data package has %d resource(s)', len(resources))

today = datetime.date.today()
aws_s3 = boto3.resource('s3')
aws_cloudwatch = boto3.client('cloudwatch')
STORAGE_BUCKET = None
if 'STORAGE_BUCKET' in os.environ:
    STORAGE_BUCKET = aws_s3.Bucket(os.environ['STORAGE_BUCKET'])
STORAGE_PREFIX = os.environ.get('STORAGE_PREFIX', '')
if len(STORAGE_PREFIX) > 0 and not STORAGE_PREFIX.endswith('/'):
    STORAGE_PREFIX += '/'
STORAGE_PREFIX += today.strftime('%Y/%m%d') + '/'


def create_data_package(_event, _context) -> object:
    """Entry point for AWS Lambda to create a data package on Amazon S3.
    """
    asyncio.run(main())
    return {
        'bucket': STORAGE_BUCKET.name,
        'prefix': STORAGE_PREFIX,
        'message': 'fetch data files from JapanPost website',
    }


def download(url, path) -> None:
    """Download a file from the given URL to the local path."""
    with urllib.request.urlopen(url) as response:
        with open(path, 'wb') as writer:
            shutil.copyfileobj(response, writer)
    logger.info('downloaded a file to "%s" of %d:, bytes',
        path, os.path.getsize(path))


def unpack(path) -> Optional[str]:
    """Extract a file whose name matches with the base name from the zip file.
    """
    basepath = path.replace('.zip', '')
    with zipfile.ZipFile(path) as zip_archive:
        for fname in zip_archive.namelist():
            if fname.lower().endswith('.csv'):
                zip_archive.extract(fname, basepath)
                return os.path.join(basepath, fname)
    return None


def convert(header, src, dst) -> int:
    """Convert a raw data file into a normalized data with the standard
    encoding."""
    logger.info('converting "%s" to "%s"', src, dst)
    normalize = partial(unicodedata.normalize, DATA_PACKAGE_NORMALIZATION_FORM)
    dstdir = os.path.dirname(dst)
    if not os.path.exists(dstdir):
        os.mkdir(dstdir)
    records = 0
    with open(src, 'r', encoding=DATA_SOURCE_ENCODING) as reader, \
         open(dst, 'w', encoding=DATA_PACKAGE_ENCODING) as writer:
        writer.write(','.join(header))
        writer.write('\n')
        for line in reader:
            writer.write(normalize(line.rstrip('\r\n')))
            writer.write('\n')
            records += 1
    return records


def upload(src, dst=None) -> None:
    """Upload a file to the S3 bucket."""
    if dst is None:
        dst = os.path.basename(src)
    key = STORAGE_PREFIX + dst
    if STORAGE_BUCKET is None:
        logger.info('MOCK - upload "%s" to "%s"', src, key)
        return
    logger.info('uploading "%s" to "%s" in "%s" bucket', src, key, STORAGE_BUCKET.name)
    STORAGE_BUCKET.Object(key).upload_file(src)


def sha256hex(path) -> str:
    """Calculate a SHA-256 digest value of the given file."""
    hasher = hashlib.sha256()
    with open(path, 'rb') as reader:
        for chunk in iter(lambda: reader.read(2048 * hasher.block_size), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


async def update_data_source(descriptor, url, cachedir='/tmp') -> None:
    """Update a data source."""
    logger.info('updating "%s" on "%s" from "%s"', descriptor['name'], descriptor['path'], url)
    local_archive = os.path.join(cachedir, descriptor['name'] + '.zip')
    local_path = os.path.join(cachedir, descriptor['path'])
    download(url, local_archive)
    csv_path = unpack(local_archive)
    fields = descriptor['schema']['fields']
    header = [f['name'] for f in fields]
    records = convert(header, csv_path, local_path)
    aws_cloudwatch.put_metric_data(
        MetricData=[
            {
                'MetricName': 'NumberOfRecords',
                'Dimensions': [
                    {
                        'Name': 'DATA_PACKAGE',
                        'Value': 'ZipcodeJP'
                    },
                    {
                        'Name': 'DATA_NAME',
                        'Value': descriptor['name']
                    },
                ],
                'Unit': 'Count',
                'Value': records,
            },
        ],
        Namespace='Dataset',
    )


async def main() -> None:
    """Drive function for creating a data package."""
    cachedir = tempfile.mkdtemp()
    tasks = []

    def lookup_resource(name):
        matched = tuple(filter(lambda r: r['name'] == name, resources))
        return matched[0] if matched else None

    for src in DATA_SOURCES:
        matched = lookup_resource(src['name'])
        if matched:
            task = asyncio.create_task(update_data_source(matched, src['url'], cachedir))
            tasks.append(task)
        else:
            logger.error('"%s" is not found on data package.', src['name'])
    await asyncio.gather(*tasks)
    logger.info('creating a ZIP package and upload it with a digest file')
    digest = {}
    zippath = os.path.join(cachedir, 'datapackage.zip')
    with zipfile.ZipFile(zippath, 'w') as archive:
        archive.write(DATA_PACKAGE, 'datapackage.json')
        datadir = os.path.join(cachedir, 'data')
        for fname in os.listdir(datadir):
            path = os.path.join(datadir, fname)
            archive.write(path, 'data/' + fname)
            digest[fname] = sha256hex(path)
    digest['datapackage.zip'] = sha256hex(DATA_PACKAGE)
    logger.info(json.dumps(digest))
    with open(os.path.join(cachedir, 'digest.json'), 'w', encoding='utf8') as writer:
        json.dump({
            'algorithm': 'sha256',
            'date': today.strftime('%Y-%m-%d'),
            'files': digest,
        }, writer, indent=2)
    upload(os.path.join(cachedir, 'digest.json'))
    upload(zippath)
    shutil.rmtree(cachedir)


if __name__ == '__main__':
    asyncio.run(main())
