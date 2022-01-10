# -*- coding: utf-8 -*-

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

with open(DATA_PACKAGE) as fp:
    package = json.load(fp)
resources = package['resources']
logger.info('the target data package has %d resource(s)', len(resources))

today = datetime.date.today()
aws_s3 = boto3.resource('s3')
aws_cloudwatch = boto3.client('cloudwatch')
bucket = None
if 'STORAGE_BUCKET' in os.environ:
    bucket = aws_s3.Bucket(os.environ['STORAGE_BUCKET'])
prefix = os.environ.get('STORAGE_PREFIX', '')
if len(prefix) > 0 and not prefix.endswith('/'):
    prefix += '/'
prefix += today.strftime('%Y/%m%d') + '/'


def create_data_package(event, context):
    """Entry point for AWS Lambda to create a data package on Amazon S3.
    """
    asyncio.run(main())
    return {
        'bucket': bucket.name,
        'prefix': prefix,
        'message': 'fetch data files from JapanPost website',
    }


def download(url, path):
    with urllib.request.urlopen(url) as response:
        with open(path, 'wb') as fp:
            shutil.copyfileobj(response, fp)
    logger.info('downloaded a file to "{}" of {:,} bytes'.format(
        path, os.path.getsize(path)))


def unpack(path):
    d = path.replace('.zip', '')
    with zipfile.ZipFile(path) as z:
        for f in z.namelist():
            if f.lower().endswith('.csv'):
                z.extract(f, d)
                return os.path.join(d, f)


def convert(header, src, dst):
    logger.info('converting "%s" to "%s"', src, dst)
    normalize = partial(unicodedata.normalize, DATA_PACKAGE_NORMALIZATION_FORM)
    d = os.path.dirname(dst)
    if not os.path.exists(d):
        os.mkdir(d)
    records = 0
    header_size = len(header)
    with open(src, 'r', encoding=DATA_SOURCE_ENCODING) as r, open(dst, 'w', encoding=DATA_PACKAGE_ENCODING) as w:
        w.write(','.join(header))
        w.write('\n')
        for line in r:
            s = normalize(line.rstrip('\r\n'))
            w.write(s)
            w.write('\n')
            records += 1
    return records


def upload(src, dst=None):
    if dst is None:
        dst = os.path.basename(src)
    key = prefix + dst
    if bucket is None:
        logger.info('MOCK - upload "%s" to "%s"', src, key)
        return
    logger.info('uploading "%s" to "%s" in "%s" bucket', src, key, bucket.name)
    bucket.Object(key).upload_file(src)


def sha256hex(path):
    m = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(2048 * m.block_size), b''):
            m.update(chunk)
    return m.hexdigest()


async def update_data_source(descriptor, url, cachedir='/tmp'):
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


async def main():
    cachedir = tempfile.mkdtemp()
    tasks = []
    for s in DATA_SOURCES:
        t = tuple(filter(lambda r: r['name'] == s['name'], resources))
        if t:
            task = asyncio.create_task(update_data_source(t[0], s['url'], cachedir))
            tasks.append(task)
        else:
            logger.error('"%s" is not found on data package.', s['name'])
    await asyncio.gather(*tasks)
    logger.info('creating a ZIP package and upload it with a digest file')
    digest = {}
    zf = os.path.join(cachedir, 'datapackage.zip')
    with zipfile.ZipFile(zf, 'w') as z:
        z.write(DATA_PACKAGE, 'datapackage.json')
        d = os.path.join(cachedir, 'data')
        for f in os.listdir(d):
            p = os.path.join(d, f)
            z.write(p, 'data/' + f)
            digest[f] = sha256hex(p)
    digest['datapackage.zip'] = sha256hex(DATA_PACKAGE)
    logger.info(json.dumps(digest))
    with open(os.path.join(cachedir, 'digest.json'), 'w') as f:
        json.dump({
            'algorithm': 'sha256',
            'date': today.strftime('%Y-%m-%d'),
            'files': digest,
        }, f, indent=2)
    upload(os.path.join(cachedir, 'digest.json'))
    upload(zf)
    shutil.rmtree(cachedir)


if __name__ == '__main__':
    asyncio.run(main())
