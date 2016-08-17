# -*- coding: utf-8 -*-
from nvesta.library.rb.classes import Undefined

__author__ = 'viruzzz-kun'


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

    def as_db_record(self):
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
        return self.as_db_record()