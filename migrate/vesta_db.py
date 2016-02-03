# -*- coding: utf-8 -*-
import pymongo

__author__ = 'viruzzz-kun'


def produce_fd(code):
    return {
        'key': code,
        'mandatory': code == 'code',
    }


def migrate():
    client = pymongo.MongoClient('10.1.2.11')

    db_vesta = client['vesta']
    db_nvesta = client['nvesta']

    for v_description in db_vesta['dict_names'].find():
        code = v_description.get('code')

        v_collection = db_vesta[code]
        n_collection = db_nvesta['refbook.' + code]

        count = v_collection.count()

        print 'Transferring', str(count).rjust(6), code

        if code == 'dict_names':
            print '...Skipped'
            continue

        field_codes = set()

        primary_link = None
        linked = v_description.get('linked')
        if linked:
            primary_link = {
                'left_field': linked['origin_field'],
                'right_field': linked['linked_field'],
                'right_rb': linked['collection']['code'],
            }

        _id = v_description.get('id')  # ?
        vers = v_description.get('version')

        if count > 0:
            n_collection.insert(v_collection.find())
            for row in v_collection.find():
                field_codes |= set(row.keys())
        else:
            print '...Not transferring data and fields'

        field_codes.discard('_id')

        n_description = {
            'code': code,
            'name': v_description.get('name') or code,
            'description': v_description.get('description'),
            'oid': v_description.get('oid'),
            'fields': map(produce_fd, sorted(field_codes)),
            'primary_link': primary_link,
        }

        db_nvesta['refbooks'].insert(n_description)


def migrate_2():
    client = pymongo.MongoClient('10.1.2.11')

    db_vesta = client['vesta']
    db_nvesta = client['nvesta']

    dont_touch_names = set(description['code'] for description in db_vesta['dict_names'].find())

    for code in db_vesta.collection_names(False):
        if code in dont_touch_names:
            continue

        v_collection = db_vesta[code]
        n_collection = db_nvesta['refbook.' + code]

        count = v_collection.count()

        print 'Transferring', str(count).rjust(6), code

        if code == 'dict_names':
            print '...Skipped'
            continue

        field_codes = set()

        primary_link = None
        linked = None

        if count > 0:
            n_collection.insert(v_collection.find())
            for row in v_collection.find():
                field_codes |= set(row.keys())
        else:
            print '...Not transferring data and fields'

        field_codes.discard('_id')

        n_description = {
            'code': code,
            'name': code,
            'description': '',
            'oid': '',
            'fields': map(produce_fd, sorted(field_codes)),
            'primary_link': primary_link,
        }

        db_nvesta['refbooks'].insert(n_description)

if __name__ == "__main__":
    migrate_2()


