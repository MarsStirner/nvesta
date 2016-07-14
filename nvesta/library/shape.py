# -*- coding: utf-8 -*-
import logging
from copy import copy

import bson
import datetime
import six

__author__ = 'viruzzz-kun'


logger = logging.getLogger(__name__)


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


class MongoObject(object):
    _default_values = {}

    def __init__(self, record=None):
        """
        @type record: dict|NoneType
        @param record:
        """
        object.__setattr__(self, 'data', {})
        if record is not None:
            self.set_record(record)

    def _copy_fields(self):
        return getattr(self, '__slots__', [])

    def _default_value(self, field):
        return self._default_values.get(field)

    def __getattr__(self, item):
        data = object.__getattribute__(self, 'data')
        flds = object.__getattribute__(self, '_copy_fields')()
        if item in flds:
            return data.get(item)
        return object.__getattribute__(self, item)

    def __setattr__(self, key, value):
        flds = object.__getattribute__(self, '_copy_fields')()
        data = object.__getattribute__(self, 'data')
        if key in flds:
            data[key] = value
        object.__setattr__(self, key, value)

    def set_record(self, record):
        """
        @type record: dict
        @param record:
        @return:
        """
        self.data.clear()
        self.data.update({
            key: record.get(key, self._default_value(key))
            for key in self._copy_fields()
            if key in record
        })
        return self

    def update(self, record):
        """
        @type record: dict
        @param record:
        @return:
        """
        self.data.update({
            key: record[key]
            for key in self._copy_fields()
            if key in record and record[key] is not Undefined
        })
        return self

    def as_record(self):
        """
        @rtype: dict
        @return:
        """
        return {
            key: self.data.get(key)
            for key in self._copy_fields()
        }

    def __json__(self):
        """
        @rtype: dict
        @return:
        """
        return self.as_record()


class RefBookRecordMeta(MongoObject):
    __slots__ = ['beg_version', 'end_version', 'delete', 'draft', 'edit']

    @classmethod
    def from_rb_meta(cls, rb_meta):
        result = cls()
        result.beg_version = rb_meta.version
        result.draft = True
        return result


class RefBookRecordControllerDescriptor(object):
    pass


class RefBookRecordController(object):
    def __init__(self, rb, record):
        self.rb = rb
        self.record = record


class RefBookRecord(object):
    """
    :type rb: RefBook
    """
    __slots__ = ['data', 'rb', 'meta']
    rb = None
    ctrl = RefBookRecordControllerDescriptor()

    def __init__(self, record=None):
        self.meta = RefBookRecordMeta()
        self.data = {}
        if record:
            self.set_record(record)

    def set_record(self, record):
        self.data.clear()
        for description in self.rb.meta.fields:
            key = description.key
            value = record.get(key, Undefined)
            if value is not Undefined:
                self.data[key] = value
            else:
                self.data[key] = None

        _id = record.get('_id', Undefined)
        if isinstance(_id, bson.ObjectId):
            self.data['_id'] = _id
        elif isinstance(_id, basestring):
            self.data['_id'] = bson.ObjectId(_id)
        elif _id is not Undefined:
            self.data.pop('_id', None)

        _meta = record.get('_meta', Undefined)
        if not (_meta is Undefined or _meta is None):
            self.meta = RefBookRecordMeta(_meta)
        elif not self.meta:
            self.meta = RefBookRecordMeta.from_rb_meta(self.rb.meta)  # TODO: set default from RefBookMeta
        self.data['_meta'] = self.meta.as_record()

    def update(self, data, weak=True):
        record = self
        if not self.meta.draft:
            if not self.meta.edit:
                record = self.__class__()
                record.update(self.data, False)
                self.meta.edit = record
            else:
                record = self.meta.edit

        skipped = set()
        for description in self.rb.meta.fields:
            key = description.key
            value = data.get(key, Undefined)
            if value is not Undefined:
                record.data[key] = value
            else:
                skipped.add(key)
        if not weak:
            for key in skipped:
                record.data[key] = None

    def save(self):
        self.rb.save(self)
        return self

    def delete(self):
        self.meta.delete = True
        return self

    def reset(self):
        if self.meta.end_version is not None:
            logger.warning(u'Resetting fixed record for some reason: _id = %s', self.data.get('_id', 'UNSAVED'))
            return
        if self.meta.edit:
            self.meta.edit = None

        if self.meta.delete:
            self.meta.delete = False

        if self.meta.draft:
            self.rb.delete_record(self)

    @classmethod
    def for_refbook(cls, refbook):
        class RefBookRecordF(RefBookRecord):
            rb = refbook
        return RefBookRecordF

    def __contains__(self, item):
        return item in self.rb.meta

    def __getitem__(self, item):
        if item in self.rb.meta:
            return self.data.get(item)

    def __setitem__(self, key, value):
        if key in self.rb.meta:
            self.data[key] = value

    def __iter__(self):
        return iter(self.data)

    def get(self, item, default=None):
        if item in self.rb.meta:
            return self.data.get(item, default)
        return default

    def __json__(self):
        result = {}
        for description in self.rb.meta.fields:
            key = description.key
            value = self.data.get(key)
            result[key] = value
            if description.link:
                add_key = description.link['key']
                rb_code = description.link['code']
                rb_field = description.link['linked_field']
                as_list = description.link.get('list')
                ref_book = RefBookRegistry.get(rb_code)
                if as_list:
                    result[add_key] = ref_book.find({rb_field: value})
                else:
                    result[add_key] = ref_book.find_one({rb_field: value})
        result['_id'] = str(self.data.get('_id'))
        result['_meta'] = self.meta
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

    def as_record(self):
        return {
            'version': self.version,
            'fix_datetime': self.fix_datetime,
        }

    __json__ = as_record


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

    def as_record(self):
        return {
            'key': self.key,
            'type': self.type,
            'mandatory': self.mandatory,
            'unique': self.unique,
            'link': self.link,
        }

    __json__ = as_record


class RefBookMeta(object):
    id = None
    oid = None
    code = None
    name = None
    description = None
    version = 0
    versions = None
    fields = None
    primary_link = None

    def __init__(self, record=None):
        self.fields = []
        if record is not None:
            self.update(record)

    @classmethod
    def from_db_record(cls, record):
        meta = RefBookMeta()
        meta.update(record)
        meta.versions = map(RefBookVersionMeta, record.get('versions', []))
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

    def to_db_record(self):
        self.__check_integrity()
        result = {
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'versions': [version.as_record for version in self.versions],
            'oid': self.oid,
            'primary_link': self.primary_link.get_rb_record(),
            'fields': [f.as_record() for f in self.fields]
        }
        return result

    def __check_integrity(self):
        if not self.versions:
            self.versions = [
                RefBookVersionMeta({
                    'version': self.version,
                    'fix_datetime': datetime.datetime.utcnow(),
                })
            ]

    def __contains__(self, item):
        for i in self.fields:
            if i.key == item:
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


class RefBook(object):
    """
    :type meta: RefBookMeta
    :type collection: pymongo.collection.Collection
    """
    meta = None
    collection = None
    record_factory = None

    def find(self, kwargs, sort=None, limit=None, skip=None, version=None):
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
        all_names = set(field.key for field in self.meta.fields)
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
        refbook.record_factory = RefBookRecord.for_refbook(refbook)
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
