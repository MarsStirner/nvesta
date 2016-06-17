#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse

import sys

import itertools

import pymongo

from hitsl_utils.safe import safe_traverse, safe_dict
from nvesta.library.shape import RefBookRegistry
from nvesta.library.nsi.client import NsiClient
from nvesta.library.nsi.data import list_nsi_dictionaries, import_nsi_dict

__author__ = 'viruzzz-kun'


url = 'http://nsi.rosminzdrav.ru/wsdl/SOAP-server.v2.php?wsdl'
key = 'd6ba79b126957042a471f8b9d880c978'
nvesta_db = 'nvesta'


def update_nsi_dicts():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_const', const=True, default=False)
    parser.add_argument('--list', action='store_const', const=True, default=False)
    parser.add_argument('--host', default=None)
    parser.add_argument('--port', default=None)
    parser.add_argument('--url', default=url)
    parser.add_argument('--key', default=key)
    parser.add_argument('--db', default=nvesta_db)

    args = parser.parse_args(sys.argv[1:])

    mongo = pymongo.MongoClient(
        host=args.host,
        port=args.port,
    )

    RefBookRegistry.bootstrap(mongo[args.db])
    client = NsiClient(url=args.url, user_key=args.key)

    print ('Retrieving data from NSI')
    listed = list_nsi_dictionaries(client)

    cooked = [
        (their['code'], their['name'], safe_traverse(our, 'version', default='?'), their.get('version', 0), their)
        for our, their in (
            (safe_dict(desc['our']), safe_dict(desc['their']))
            for desc in listed
        )
    ]

    if args.list:
        for code, name, our, their, nsi_dict in cooked:
            print('%s %s %s->%s' % (code, name, our, their))
    elif args.all:
        to_update = [
            (code, name, our, their, nsi_dict)
            for code, name, our, their, nsi_dict in cooked
            if their != our
        ]
        for code, name, our, their, nsi_dict in to_update:
            print('%s %s %s->%s' % (code, name, our, their))
            print 'Updating (%s) %s...' % (code, name)
            import_nsi_dict(nsi_dict, client)
        if not to_update:
            print ('Nothing to update')


def migrate_from_v1():
    def produce_fd(code):
        return {
            'key': code,
            'mandatory': code == 'code',
        }

    def blocks(iterable, max_size=2000):
        result = []
        i = 0
        for item in iterable:
            result.append(item)
            i += 1
            if i >= max_size:
                yield result
                result = []
                i = 0
        if result:
            yield result

    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_const', const=True, default=False)
    parser.add_argument('--host', default=None)
    parser.add_argument('--port', default=None)
    parser.add_argument('--from-db', default='vesta')
    parser.add_argument('--db', default=nvesta_db)

    args = parser.parse_args(sys.argv[1:])

    mongo = pymongo.MongoClient(
        host=args.host,
        port=args.port,
    )

    RefBookRegistry.bootstrap(mongo[args.db])

    db_vesta = mongo[args.from_db]
    RefBookRegistry.bootstrap(mongo[args.db])

    for v_description in db_vesta['dict_names'].find():
        code = v_description.get('code')
        v_collection = db_vesta[code]
        count = v_collection.count()

        print 'Transferring', str(count).rjust(6), code

        if code == 'dict_names':
            print '...Skipped'
            continue

        field_codes = set()
        for row in v_collection.find():
            field_codes |= set(row.keys())
        field_codes.discard('_id')

        primary_link = None
        linked = v_description.get('linked')
        if linked:
            primary_link = {
                'left_field': linked['origin_field'],
                'right_field': linked['linked_field'],
                'right_rb': linked['collection']['code'],
            }

        rb = RefBookRegistry.create({
            'code': code,
            'name': v_description.get('name') or code,
            'description': v_description.get('description'),
            'oid': v_description.get('oid'),
            'fields': [{
                'key': fc,
                'mandatory': fc == 'code',
            } for fc in sorted(field_codes)],
            'primary_link': primary_link,
            'version': safe_traverse(v_description, 'version', 'version', default=None)
        })
        rb.meta.reshape()

        for block in blocks(v_collection.find()):
            rb.save_bulk(rb.record_factory(raw) for raw in block)

