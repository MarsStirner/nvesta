# -*- coding: utf-8 -*-
import datetime

import bson
import six

__author__ = 'viruzzz-kun'


class PrimaryLinkMeta(object):
    left_rb_obj = None
    left_field = None
    right_rb_code = None
    right_field = None

    def __init__(self, left_rb, data=None):
        self.left_rb_obj = left_rb
        if data:
            self.update(data)

    def as_db_record(self):
        if self.left_field and self.right_rb_code and self.right_field:
            return {
                'left_field': self.left_field,
                'right_rb': self.right_rb_code,
                'right_field': self.right_field,
            }
        else:
            return None

    def update(self, data):
        self.left_field = data.get('left_field')
        self.right_rb_code = data.get('right_rb')
        self.right_field = data.get('right_field')

    def __json__(self):
        return self.as_db_record()


class RefBookVersionMeta(object):
    __slots__ = ['version', 'fix_datetime']

    def __init__(self, record=None):
        self.version = None
        self.fix_datetime = None

        if record is not None:
            self.update(record)

    def update(self, record):
        self.version = record.get('version')
        self.fix_datetime = record.get('fix_datetime')

    def as_db_record(self):
        return {
            'version': self.version,
            'fix_datetime': self.fix_datetime,
        }

    def __json__(self):
        return self.as_db_record()


class FieldMeta(object):
    __slots__ = ['key', 'type', 'mandatory', 'unique', 'link']

    def __init__(self, record=None, **kwargs):
        self.key = None
        self.type = None
        self.mandatory = False
        self.unique = False
        self.link = None
        if record is not None:
            self.update(record)
        for k, v in six.iteritems(kwargs):
            if k in self.__slots__:
                setattr(self, k, v)

    def update(self, record):
        if not record:
            record = {}
        self.key = record.get('key')
        self.type = record.get('type') or 'string'
        self.mandatory = record.get('mandatory', False)
        self.unique = record.get('unique', False)
        self.link = record.get('link')

    def as_db_record(self):
        return {
            'key': self.key,
            'type': self.type,
            'mandatory': self.mandatory,
            'unique': self.unique,
            'link': self.link,
        }

    def __json__(self):
        return self.as_db_record()


class RefBookMeta(object):
    id = None
    oid = None
    code = None
    name = None
    description = None
    version = '1'
    versions = None
    fields = None
    primary_link = None

    def __init__(self, record=None):
        self.fields = []
        if record is not None:
            self.update(record)

    @classmethod
    def from_db_record(cls, record):
        meta = cls()
        meta.update(record)
        meta.versions = map(RefBookVersionMeta, record.get('versions', []))
        meta.__check_integrity()
        return meta

    def update(self, record):
        if isinstance(record.get('_id'), bson.ObjectId):
            self.id = record['_id']
        elif isinstance(record.get('_id'), basestring):
            self.id = bson.ObjectId(record['_id'])
        else:
            self.id = None
        self.code = record.get('code')
        self.name = record.get('name') or record.get('code')
        self.description = record.get('description')
        self.version = record.get('version')
        self.oid = record.get('oid')
        self.primary_link = PrimaryLinkMeta(self, record.get('primary_link'))
        self.fields = map(FieldMeta, record.get('fields', []))

    def as_db_record(self):
        self.__check_integrity()
        result = {
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'versions': [version.as_db_record() for version in self.versions],
            'oid': self.oid,
            'primary_link': self.primary_link.as_db_record(),
            'fields': [f.as_db_record() for f in self.fields],
        }
        return result

    def __check_integrity(self):
        if self.version is None:
            self.version = '1'

        if not self.versions:
            self.versions = [
                RefBookVersionMeta({
                    'version': self.version,
                    'fix_datetime': datetime.datetime.utcnow(),
                })
            ]
            self.reshape()

    def __contains__(self, item):
        for i in self.fields:
            if i.key == item:
                return True
        return False

    def reshape(self):
        from nvesta.library.rb.registry import RefBookRegistry

        if self.id:
            existing = RefBookRegistry.db['refbooks'].find_one({'_id': self.id})
            if existing:
                prev_code = existing['code']
                if prev_code != self.code:
                    RefBookRegistry.db['refbooks.%s' % prev_code].rename('refbooks.%s' % self.code)
            RefBookRegistry.db['refbooks'].update_one(
                {'_id': self.id},
                {'$set': self.as_db_record()},
                True
            )
        else:
            RefBookRegistry.db['refbooks'].insert(
                self.as_db_record(),
            )

    def __json__(self):
        self.__check_integrity()
        result = {
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'fields': self.fields,
            'version': self.version,
            'versions': self.versions,
            'oid': self.oid,
            'primary_link': self.primary_link,
            '_id': str(self.id) if isinstance(self.id, bson.ObjectId) else self.id
        }
        return result