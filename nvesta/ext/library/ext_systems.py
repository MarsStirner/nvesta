# -*- coding: utf-8 -*-
from bson.objectid import ObjectId
from pymongo.errors import DuplicateKeyError

__author__ = 'viruzzz-kun'


class ExtSystemCodeDuplicate(Exception):
    pass


class ExtSystemProperties(object):
    collection = None

    def __init__(self, record=None):
        self.id = None
        self.code = None
        self.name = None
        self.codes = []
        if record:
            self.set_db_record(record)

    def set_db_record(self, record):
        id_ = record.get('_id', None)
        if isinstance(id_, basestring):
            self.id = ObjectId(id_)
        elif isinstance(id_, ObjectId):
            self.id = id_
        else:
            self.id = None

        self.code = record['code']
        self.name = record.get('name') or self.code
        self.codes = record.get('refbooks') or []

    def update(self, record):
        self.code = record['code']
        self.name = record.get('name') or self.code
        self.codes = [rb['code'] for rb in (record.get('refbooks') or [])]

    @property
    def refbooks_metas(self):
        from nvesta.library.rb.registry import RefBookRegistry
        return [
            RefBookRegistry.get(code).meta
            for code in self.codes
            if RefBookRegistry.get(code)
        ]

    @property
    def refbooks_dict(self):
        from nvesta.library.rb.registry import RefBookRegistry
        return {
            code: RefBookRegistry.get(code)
            for code in self.codes
            if RefBookRegistry.get(code)
        }

    def as_db_record(self, with_id=False):
        result = {
            'code': self.code,
            'name': self.name,
            'refbooks': self.codes,
        }
        if self.id and with_id:
            result['_id'] = self.id
        return result

    def as_json(self):
        result = {
            'code': self.code,
            'name': self.name,
            'refbooks': self.refbooks_metas,
        }
        if self.id:
            result['_id'] = str(self.id)
        else:
            result['_id'] = None
        return result

    def __json__(self):
        return self.as_json()

    def save(self):
        try:
            if self.id:
                self.collection.update_one(
                    {'_id': self.id},
                    {'$set': self.as_db_record()}
                )
            else:
                self.id = self.collection.insert(self.as_db_record())
        except DuplicateKeyError:
            raise ExtSystemCodeDuplicate(self.code)

    def delete(self):
        if self.id:
            self.collection.delete_one({'_id': self.id})

    @classmethod
    def find_by_code(cls, code):
        result = cls.collection.find_one({'code': code})
        if result:
            return cls(result)

    @classmethod
    def all(cls):
        return map(cls, cls.collection.find({}))

    @classmethod
    def bootstrap(cls, mongodb):
        cls.collection = mongodb['integrations']
        cls.collection.create_index('code', unique=True)
