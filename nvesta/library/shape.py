# -*- coding: utf-8 -*-
from copy import copy

import bson

__author__ = 'viruzzz-kun'


# __meta = {
#     '_id': bson.ObjectId(''),
#     'code': 'rbPolicyType',
#     'name': u'Тип полиса',
#     'fields': [
#         {
#             'key': 'code',
#             'type': 'str',
#             'unique': True,
#             'mandatory': True,
#         }, {
#             'key': 'name',
#             'type': 'str',
#             'unique': True,
#             'mandatory': True,
#         }, {
#             'code': 'TFOMSCode',
#             'link': {
#                 'code': 'NK0469',
#                 'linked_field': 'code',
#                 'list': False,
#                 'key': 'nsi',
#             }
#         }
#     ],
# }


class Undefined(object):
    pass


class RefBookRecord(object):
    """
    :type meta: RefBookMeta
    """
    meta = None

    def __init__(self, record=None):
        self.data = {}
        if record:
            self.update(record)

    def update(self, record):
        for description in self.meta.fields:
            key = description['key']
            value = record.get(key, Undefined)
            if value is not Undefined:
                self.data[key] = value
        _id = record.get('_id', Undefined)
        if isinstance(_id, bson.ObjectId):
            self.data['_id'] = _id
        elif isinstance(_id, basestring):
            self.data['_id'] = bson.ObjectId(_id)
        elif _id is Undefined:
            pass
        else:
            self.data.pop('_id', None)

    @classmethod
    def for_meta(cls, rb_meta):
        class RefBookRecordF(RefBookRecord):
            meta = rb_meta
        return RefBookRecordF

    def __contains__(self, item):
        return item in self.meta

    def __getitem__(self, item):
        if item in self.meta:
            return self.data.get(item)

    def __setitem__(self, key, value):
        if key in self.meta:
            self.data[key] = value

    def get(self, item, default=None):
        if item in self.meta:
            return self.data.get(item, default)
        return default

    @property
    def id(self):
        return self.data.get('_id')

    def __json__(self):
        result = {}
        for description in self.meta.fields:
            key = description['key']
            value = self.data.get(key)
            result[key] = value
            if description.get('link'):
                add_key = description['link']['key']
                rb_code = description['link']['code']
                rb_field = description['link']['linked_field']
                as_list = description['link'].get('list')
                ref_book = RefBookRegistry.get(rb_code)
                if as_list:
                    result[add_key] = ref_book.find({rb_field: value})
                else:
                    result[add_key] = ref_book.find_one({rb_field: value})
        result['_id'] = str(self.data.get('_id'))
        return result


class PrimaryLinkMeta(object):
    left_rb_obj = None
    left_field = None
    right_rb_code = None
    right_field = None

    def __init__(self, left_rb, data=None):
        self.left_rb_obj = left_rb
        if data:
            self.update(data)

    def get_rb_record(self):
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
        return self.get_rb_record()


class RefBookMeta(object):
    id = None
    oid = None
    code = None
    name = None
    description = None
    version = 0
    fields = None
    primary_link = None

    def __init__(self, record=None):
        if record is not None:
            self.update(record)

    @classmethod
    def from_db_record(cls, record):
        meta = RefBookMeta()
        meta.update(record)
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
        self.fields = [
            {
                'key': field.get('key'),
                'type': field.get('type') or 'string',
                'mandatory': field.get('mandatory'),
                'unique': field.get('unique'),
                'link': field.get('link'),
            }
            for field in record.get('fields', [])
        ]

    def to_db_record(self):
        result = {
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'oid': self.oid,
            'primary_link': self.primary_link.get_rb_record(),
            'fields': self.fields
        }
        return result

    def __contains__(self, item):
        for i in self.fields:
            if i.get('key') == item:
                return True
        return False

    def reshape(self):
        if self.id:
            existing = RefBookRegistry.db['refbooks'].find_one({'_id': self.id})
            if existing:
                prev_code = existing['code']
                if prev_code != self.code:
                    RefBookRegistry.db['refbooks.%s' % prev_code].rename('refbooks.%s' % self.code)
            RefBookRegistry.db['refbooks'].update_one(
                {'_id': self.id},
                {'$set': self.to_db_record()},
                True
            )
        else:
            RefBookRegistry.db['refbooks'].insert(
                self.to_db_record(),
            )

    def __json__(self):
        result = {
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'fields': self.fields,
            'version': self.version,
            'oid': self.oid,
            'primary_link': self.primary_link,
            '_id': str(self.id) if isinstance(self.id, bson.ObjectId) else self.id
        }
        return result


class RefBook(object):
    """
    :type meta: RefBookMeta
    :type collection: pymongo.collection.Collection
    """
    meta = None
    collection = None
    record_factory = None

    def find(self, kwargs, sort=None, limit=None, skip=None):
        kwargs = self._prepare_search_params(kwargs)
        cursor = self.collection.find(kwargs)
        if limit:
            cursor = cursor.limit(limit)
        if skip:
            cursor = cursor.skip(skip)
        if sort:
            cursor = cursor.sort(sort)
        return map(
            self.record_factory,
            cursor,
        )

    def find_one(self, kwargs, rec_id=Undefined):
        """
        :param kwargs:
        :return:
        :rtype: RefBookRecord
        """
        if rec_id is not Undefined:
            if kwargs == '_id' and isinstance(rec_id, basestring):
                rec_id = bson.ObjectId(rec_id)
            return self.record_factory(self.collection.find_one({kwargs: rec_id}))
        else:
            return self.record_factory(self.collection.find_one(kwargs))

    def _prepare_search_params(self, kwargs):
        if not len(kwargs.keys()):
            return {}
        elif 'query' in kwargs:
            return {
                '$or': [
                    {
                        'name': {'$regex': kwargs['query'], '$options': 'i'}
                    },
                    {
                        'code': {'$regex': kwargs['query'], '$options': 'i'}
                    }
                ]
            }
        elif len(kwargs.keys()) == 1:
            field_name = kwargs.keys()[0]
            # if refbook has field field_name...
            return {
                field_name: {'$regex': kwargs[field_name], '$options': 'i'}
            }
        else:
            parts = [(f, v) for f, v in kwargs.iteritems()]  # if refbook has field f...
            return {
                '$and': [
                    {
                        field_name: {'$regex': field_val, '$options': 'i'}
                    }
                    for field_name, field_val in parts
                ]
            }

    def save(self, rb_record):
        """
        :type rb_record: RefBookRecord
        :param rb_record:
        :return:
        """
        data = copy(rb_record.data)
        _id = data.pop('_id', Undefined)
        if _id is not Undefined:
            self.collection.update_one(
                {'_id': _id},
                {'$set': data},
                True
            )
        else:
            self.collection.insert_one(data)
        return rb_record

    def save_bulk(self, rb_records):
        from pymongo import InsertOne, UpdateOne, WriteConcern

        def make_request(data):
            _id = data.pop('_id', Undefined)
            if _id is Undefined:
                return InsertOne(data)
            else:
                return UpdateOne(
                    {'_id': _id},
                    {'$set': data},
                    True
                )
        requests = [make_request(copy(rb_record.data)) for rb_record in rb_records]
        self.collection.bulk_write(requests)

    def ensure_default_indexes(self):
        all_names = set(field['key'] for field in self.meta.fields)
        key_names = (key for key in ('code', 'id', 'recid', 'oid') if key in all_names)
        for name in key_names:
            self.collection.create_index(name, sparse=True)

    def get_primary_linked_rb(self):
        if self.meta.primary_link.right_rb_code:
            return RefBookRegistry.get(self.meta.primary_link.right_rb_code)


class RefBookRegistry(object):
    ref_books = {}
    db = None

    @classmethod
    def refbook_from_meta(cls, meta):
        refbook = RefBook()
        refbook.meta = meta
        refbook.collection = cls.db['refbook.%s' % meta.code]
        refbook.record_factory = RefBookRecord.for_meta(meta)
        cls.ref_books[meta.code] = refbook

        return refbook

    @classmethod
    def get(cls, code):
        """
        :param code:
        :return:
        :rtype: RefBook
        """
        if code not in cls.ref_books:
            raw_meta = cls.db['refbooks'].find_one({'code': code})
            if not raw_meta:
                raise KeyError(code)
            meta = RefBookMeta.from_db_record(raw_meta)
            return cls.refbook_from_meta(meta)
        return cls.ref_books[code]

    @classmethod
    def create(cls, raw_meta):
        existing = cls.db['refbooks'].find_one({'code': raw_meta['code']})
        if existing:
            raise ValueError(raw_meta['code'])
        raw_meta.pop('_id', None)
        meta = RefBookMeta.from_db_record(raw_meta)
        meta.id = cls.db['refbooks'].insert(meta.to_db_record())
        cls.db.create_collection('refbook.%s' % meta.code)
        meta.reshape()
        return cls.refbook_from_meta(meta)

    @classmethod
    def names(cls):
        return [description['code'] for description in cls.db['refbooks'].find()]

    @classmethod
    def list(cls):
        names = cls.db['refbooks'].find()
        return [
            cls.get(description['code'])
            for description in names
        ]

    @classmethod
    def bootstrap(cls, mongo_db):
        cls.db = mongo_db
        collection_names = cls.db.collection_names(False)
        if 'refbooks' not in collection_names:
            cls.db.create_collection('refbooks')
        for rb in cls.list():
            rb.ensure_default_indexes()

    @classmethod
    def invalidate(cls, code=None):
        if code is not None:
            cls.ref_books.pop(code, None)
        else:
            cls.ref_books.clear()
