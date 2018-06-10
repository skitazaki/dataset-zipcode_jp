#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Generate Prefecture and City list from *ken_all* files.
'''

import io
import logging
import logging.config
import pathlib

import datapackage
import pandas as pd

__version__ = '0.4.0'

SCRIPTPATH = pathlib.Path(__file__)
APPNAME = SCRIPTPATH.stem
BASEDIR = SCRIPTPATH.parent.parent.resolve()

LOGGINGCONFIG_NAME = 'logging.yml'
LOGGINGCONFIG_FILE = SCRIPTPATH.parent.joinpath(LOGGINGCONFIG_NAME)

DATAPACKAGE_NAME = 'datapackage.json'
DATAPACKAGE_FILE = BASEDIR.joinpath(DATAPACKAGE_NAME)

if LOGGINGCONFIG_FILE.exists():
    import yaml
    cfg = yaml.load(LOGGINGCONFIG_FILE.open())
    logging.config.dictConfig(cfg)


def integrate_prefecture(df_k, df_o, df_r):
    df_k['prefecture_code'] = df_k['jis_code'].apply(lambda s: s[:2])
    pref1 = df_k[
        ['prefecture_code', 'prefecture', 'prefecture_kana']].drop_duplicates(
        ).rename(columns={'prefecture_kana': 'prefecture_kogaki'})
    pref1['prefecture_type'] = pref1['prefecture'].apply(lambda s: s[-1:])
    pref2 = df_o[['prefecture', 'prefecture_kana']].drop_duplicates().rename(
        columns={'prefecture_kana': 'prefecture_oogaki'})
    pref3 = df_r[['prefecture', 'prefecture_roman']].drop_duplicates()
    pref3['prefecture_roman'] = pref3['prefecture_roman'].apply(str.title)
    pref = pref1.merge(pref2, on='prefecture').merge(pref3, on='prefecture')
    pref = pref.rename(columns={'prefecture': 'prefecture_name'})
    col = ['prefecture_code', 'prefecture_name', 'prefecture_type',
           'prefecture_kogaki', 'prefecture_oogaki', 'prefecture_roman']
    return pref[col]


def integrate_city(df_k, df_o, df_r):
    city1 = df_k[
        ['jis_code', 'prefecture', 'city', 'city_kana']].drop_duplicates(
        ).rename(columns={'jis_code': 'city_code', 'city_kana': 'city_kogaki'})
    city1['city_type'] = city1['city'].apply(lambda s: s[-1:])
    city2 = df_o[['prefecture', 'city', 'city_kana']].drop_duplicates(
        ).rename(columns={'city_kana': 'city_oogaki'})
    city3 = df_r[['prefecture', 'city', 'city_roman']].drop_duplicates()
    city3['city_roman'] = city3['city_roman'].apply(str.title)
    city3['city_sep'] = city3['city']
    city3['city_levels'] = city3['city_sep'].apply(
        lambda s: len(s.split())).map(int)
    city1['key'] = city1['prefecture'] + city1['city']
    city2['key'] = city2['prefecture'] + city2['city']
    city3['key'] = city3['prefecture'] + city3['city'].map(
        lambda s: s.replace(' ', ''))
    city = city1.merge(city2[['key', 'city_oogaki']], on='key').merge(
        city3[['key', 'city_roman', 'city_sep', 'city_levels']], on='key')
    city = city.drop('key', axis=1)
    city = city.rename(
        columns={'city': 'city_name', 'prefecture': 'prefecture_name'})
    city['prefecture_code'] = city['city_code'].apply(lambda s: s[:2])
    col = ['prefecture_code', 'prefecture_name',
           'city_code', 'city_name', 'city_type', 'city_levels', 'city_sep',
           'city_kogaki', 'city_oogaki', 'city_roman']
    return city[col]


def main():
    logger = logging.getLogger(APPNAME)
    logger.info('load datapackage file: %s', DATAPACKAGE_FILE)
    p = datapackage.Package(str(DATAPACKAGE_FILE))
    logger.info('package has %d resources', len(p.resources))
    dfs = []
    for r in ('ken_all_kogaki', 'ken_all_oogaki', 'ken_all_roman'):
        buffer = io.StringIO()
        df = pd.DataFrame(p.get_resource(r).read(keyed=True))
        df.info(buf=buffer)
        logger.info('ken_all_kogaki: %s', buffer.getvalue())
        dfs.append(df)
    df = integrate_prefecture(dfs[0], dfs[1], dfs[2])
    output = 'data/prefecture.csv'
    logger.info('write prefecture file: %s %s', output, df.shape)
    df.to_csv(output, index=False)
    df = integrate_city(dfs[0], dfs[1], dfs[2])
    output = 'data/city.csv'
    logger.info('write city file: %s %s', output, df.shape)
    df.to_csv(output, index=False)


if __name__ == '__main__':
    main()

# vim: set et ts=4 sw=4 cindent fileencoding=utf-8 :
