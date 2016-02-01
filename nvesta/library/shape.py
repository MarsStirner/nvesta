# -*- coding: utf-8 -*-
import bson

from nvesta.systemwide import mongo

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
            value = record.get(key)
            self.data[key] = value
        _id = record.get('_id')
        if isinstance(_id, bson.ObjectId):
            self.data['_id'] = _id
        elif isinstance(_id, basestring):
            self.data['_id'] = bson.ObjectId(_id)
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
        self.name = record.get('name')
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
            'version': self.version,
            'oid': self.oid,
            'primary_link': self.primary_link.get_rb_record(),
            'fields': self.fields
        }
        return result

    def __contains__(self, item):
        for i in self.fields:
            if i.get('code') == item:
                return True
        return False

    def reshape(self):
        if self.id:
            mongo.db['refbooks'].update_one(
                {'_id': self.id},
                {'$set': self.to_db_record()},
                True
            )
        else:
            mongo.db['refbooks'].insert(
                self.to_db_record(),
            )

    def __json__(self):
        result = {
            'code': self.code,
            'name': self.name,
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

    def find_one(self, kwargs):
        """
        :param kwargs:
        :return:
        :rtype: RefBookRecord
        """
        return self.record_factory(self.collection.find_one(kwargs))

    def save(self, rb_record):
        """
        :type rb_record: RefBookRecord
        :param rb_record:
        :return:
        """
        data = rb_record.data
        if data.get('_id'):
            self.collection.replace_one(
                {'_id': data['_id']},
                data,
                True
            )
        else:
            data['_id'] = self.collection.insert(data)
        return rb_record

    def get_primary_linked_rb(self):
        if self.meta.primary_link.right_rb_code:
            return RefBookRegistry.get(self.meta.primary_link.right_rb_code)


class RefBookRegistry(object):
    ref_books = {}

    @classmethod
    def refbook_from_meta(cls, meta):
        refbook = RefBook()
        refbook.meta = meta
        refbook.collection = mongo.db['refbook.%s' % meta.code]
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
            raw_meta = mongo.db['refbooks'].find_one({'code': code})
            if not raw_meta:
                raise Exception
            meta = RefBookMeta.from_db_record(raw_meta)
            return cls.refbook_from_meta(meta)
        return cls.ref_books[code]

    @classmethod
    def create(cls, code, name):
        existing = mongo.db['refbooks'].find_one({'code': code})
        if existing:
            raise Exception
        meta = RefBookMeta.from_db_record({
            'name': name,
            'code': code,
            'fields': [],
        })
        meta.id = mongo.db['refbooks'].insert(meta.to_db_record())
        mongo.db.create_collection('refbook.%s' % code)
        return cls.refbook_from_meta(meta)

    @classmethod
    def list(cls):
        names = mongo.db['refbooks'].find()
        return [
            cls.get(description['code'])
            for description in names
        ]

    @classmethod
    def bootstrap(cls):
        collection_names = mongo.db.collection_names(False)
        if 'refbooks' not in collection_names:
            mongo.db.create_collection('refbooks')

    @classmethod
    def invalidate(cls, code=None):
        if code is not None:
            cls.ref_books.pop(code, None)
        else:
            cls.ref_books.clear()
