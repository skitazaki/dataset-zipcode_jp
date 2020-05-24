#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Pull Zip archive, extract CSV file, and convert encoding into UTF-8.
"""

import asyncio
import csv
import datetime
import hashlib
import logging
import logging.config
import json
import shutil
import tempfile
import unicodedata
import zipfile
from functools import partial
from pathlib import Path
from urllib.request import urlretrieve

APPNAME = Path(__file__).stem
VERSION = '0.3.0'

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "datefmt": '%Y-%m-%d %H:%M:%S',
            "format": '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "dataset": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
        "": {
            "level": "INFO",
            "handlers": ["console",],
        },
    },
}

ORIGINAL_ENCODING = 'cp932'  # Downloaded file encoding
ENCODING = 'utf-8'  # Follow "Open Data Protocol"
NORMALIZATION_FORM = 'NFKC'
DATA_PACKAGE = Path(__file__).parent.parent / 'datapackage.json'
DATA_DIR = DATA_PACKAGE.parent / 'data'

REMOTE_DIR = "https://www.post.japanpost.jp/zipcode/dl"
REMOTE_URLS = {
    "ken_all_oogaki": REMOTE_DIR + "/oogaki/zip/ken_all.zip",
    "ken_all_kogaki": REMOTE_DIR + "/kogaki/zip/ken_all.zip",
    "ken_all_roman": REMOTE_DIR + "/roman/ken_all_rome.zip",
    "facility": REMOTE_DIR + "/jigyosyo/zip/jigyosyo.zip",
}


async def pulldata(resource, url, /, basedir=None, cachedir=None, logger=None):
    if basedir is None:
        basedir = Path.cwd()
    if cachedir is None:
        cachedir = Path.cwd()
    if logger is None:
        logger = logging.getLogger('pulldata')
    local_path = basedir / resource['path']
    local_archive = cachedir / f'{resource["name"]}.zip'
    if local_path.exists():
        logger.info(f'file already exists: {resource["name"]} at {resource["path"]}')
        return
    if local_archive.exists():
        logger.info(f'archive file is already downloaded: {local_archive.name}')
    else:
        logger.info(f'downloading archive file from: {url}')
        urlretrieve(url, local_archive)
        stats = local_archive.stat()
        logger.info(f'downloaded archive file as: {local_archive.name} ({stats.st_size:,} bytes)')
    if not local_path.parent.exists():
        local_path.parent.mkdir()
        logger.info(f'created data directory: {local_path.parent}')
    output = local_path.open('w', encoding=ENCODING)
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    fields = resource['schema']['fields']
    header = [f['name'] for f in fields]
    writer.writerow(header)
    normalize = partial(unicodedata.normalize, NORMALIZATION_FORM)
    counter = 0
    with zipfile.ZipFile(local_archive) as z:
        csv_files = [f for f in z.namelist() if f.lower().endswith('.csv')]
        if len(csv_files) > 1:
            logger.error(f'zip archive contains multiple csv files: {", ".join(csv_files)}')
            return
        with z.open(csv_files[0]) as fp:
            reader = csv.reader(map(lambda s: normalize(s.decode(ORIGINAL_ENCODING)), fp))
            for row in reader:
                writer.writerow(row)
                counter += 1
    output.close()
    stats = local_path.stat()
    logger.info(f'wrote {counter:,} records into {local_path.name} ({stats.st_size:,} bytes)')


def sha256hex(path):
    """Calculates SHA-256 and returns its hex representation.
    """
    m = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(2048 * m.block_size), b''):
            m.update(chunk)
    return m.hexdigest()


def setup_logger(verbosity=logging.INFO):
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(APPNAME)
    return logger


async def main():
    logger = setup_logger()
    if not DATA_PACKAGE.exists():
        logger.error(f'datapackage file is not found: {DATA_PACKAGE.resolve()}')
        return
    with DATA_PACKAGE.open() as fp:
        package = json.load(fp)
    resources = package['resources']
    logger.info(f'datapackage "{package["name"]}" has {len(resources)} resources')
    cachedir = Path(tempfile.mkdtemp())
    logger.debug(f'created a cache directory: {cachedir}')
    basedir = DATA_PACKAGE.parent
    pull = partial(pulldata, basedir=basedir, cachedir=cachedir, logger=logger)
    tasks = []
    for resource in resources:
        url = REMOTE_URLS[resource['name']]
        task = asyncio.create_task(pull(resource, url))
        tasks.append(task)
    await asyncio.gather(*tasks)
    shutil.rmtree(cachedir)
    logger.debug(f'cleaned up a cache directory: {cachedir}')
    logger.info('calculating hash values over resource data files.')
    digest = {}
    for resource in resources:
        local_path = basedir / resource['path']
        hashvalue = sha256hex(local_path)
        stats = local_path.stat()
        digest[resource["name"]] = {
            "bytes": stats.st_size,
            "hash": f"sha256:{hashvalue}",
        }
        logger.info(f' - {resource["name"]}: sha256:{hashvalue} on {resource["path"]}')
    digest_file = basedir / 'datapackage-digest.json'
    if digest_file.exists():
        logger.warning(f'overwrite a digest file: {digest_file}')
    now = datetime.datetime.now()
    with digest_file.open('w') as fp:
        json.dump({
            "downloaded_at": f"{now:%Y-%m-%d %H:%M:%S}",
            "resources": digest,
        }, fp, indent=2)
    logger.info(f'wrote a digest file: {digest_file}')

if __name__ == '__main__':
    asyncio.run(main())
