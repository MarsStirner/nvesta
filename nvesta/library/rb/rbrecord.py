# -*- coding: utf-8 -*-
import logging
from copy import copy

import bson
import six

from nvesta.library.rb.classes import Undefined

__author__ = 'viruzzz-kun'

logger = logging.getLogger(__name__)


class RefBookRecordMeta(object):
    __slots__ = ['beg_version', 'end_version', 'delete', 'draft', 'edit']

    def __init__(self, db_record=None):
        self.beg_version = None
        self.end_version = None
        self.delete = False
        self.draft = False
        self.edit = None
        if db_record:
            self.set_record(db_record)

    def set_record(self, db_record):
        self.beg_version = db_record.get('beg_version', None)
        self.end_version = db_record.get('end_version', None)
        self.delete = db_record.get('delete', False)
        self.draft = db_record.get('draft', False)
        self.edit = db_record.get('edit', None)

    def update(self, data):
        for key, value in six.iteritems(data):
            if key in self.__slots__:
                setattr(self, key, value)
        return self

    def as_db_record(self):
        return {
            key: getattr(self, key)
            for key in self.__slots__
        }

    def __json__(self):
        return self.as_db_record()

    @classmethod
    def from_rb_meta(cls, rb_meta):
        result = cls()
        result.beg_version = rb_meta.version
        return result


class RefBookRecord(object):
    """
    :type rb: RefBook
    """
    __slots__ = ['data', 'rb', 'meta', '_id']
    rb = None

    def __init__(self, record=None):
        self.meta = meta = RefBookRecordMeta.from_rb_meta(self.rb.meta)
        meta.draft = True
        self.data = {}
        self._id = None
        if record:
            self.set_rb_record(record)

    # DB Data Manipulations

    def set_rb_record(self, record):
        """
        Загрузка документа из БД в объект
        @param record: Документ в БД
        @type record: dict
        """
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
            self._id = _id
        elif isinstance(_id, basestring):
            self._id = bson.ObjectId(_id)
        elif _id is not Undefined:
            self._id = None

        _meta = record.get('_meta', Undefined)
        if not (_meta is Undefined or _meta is None):
            self.meta = RefBookRecordMeta(_meta)
        elif not self.meta:
            self.meta = meta = RefBookRecordMeta.from_rb_meta(self.rb.meta)
            meta.draft = True

    def as_db_record(self, with_id=False):
        """
        Преобразование записи к документу БД
        @return: Документ
        @rtype: dict
        """
        if self._id and with_id:
            return dict(
                self.data,
                _id=self._id,
                _meta=self.meta.as_db_record(),
            )
        else:
            return dict(
                self.data,
                _meta=self.meta.as_db_record(),
            )

    # Basic Data Manipulations

    def update(self, record, weak=True):
        """
        Обновление данных записи.
        - Если запись не завиксирована в справочнике, то редактируется на месте
        - Если зафиксирована, но отредактирована, то изменяется редактируемая версия (._meta.edit)
        - Если зафиксирована, но не отредактирована, то создаётся редактируемая версия и п.2
        @param record: свежие данные для редактирования
        @param weak: если True, то запись PATCH-ится, иначе перезаписывается
        """
        if self.meta.draft:
            # Если это драфт для следующей версии, но меняем его на месте
            data = self.data
        else:
            if self.meta.edit is None:
                # Если это не драфт, но и не изменённая прежде запись, создаём новую версию
                self.meta.edit = data = copy(self.data)
            else:
                # Если это не драфт, и он уже редактировался, берём редактируемую версию
                data = self.meta.edit

        skipped = set()  # здесь будут сохраняться коды полей, которые не присутствуют в передаваемом документе
        for description in self.rb.meta.fields:
            key = description.key
            value = record.get(key, Undefined)
            if value is not Undefined:
                data[key] = value
            else:
                skipped.add(key)

        if not weak:
            for key in skipped:
                data[key] = None

        if self.meta.edit == self.data:
            # Если изменённая версия идентична имеющейся, считаем запись неизменённой
            self.meta.edit = None

        self.meta.delete = False  # запись не будет считаться удалённой

        return self

    def delete(self):
        """
        Удаление записи из справочника
        """
        if not self.meta.end_version:
            self.meta.delete = True
            self.meta.edit = None
        return self

    def reset(self):
        """
        Откат всех изменений версии к фиксированной
        @return:
        """
        if self.meta.end_version is not None:
            logger.warning(u'Resetting fixed record for some reason: _id = %s', self.data.get('_id', 'UNSAVED'))
            return

        if self.meta.edit:
            self.meta.edit = None

        if self.meta.delete:
            self.meta.delete = False

        if self.meta.draft:
            self.rb.delete_record(self)

    # Auxiliary helpers

    def save(self):
        self.rb.save(self)
        return self

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

    def as_json(self, edge=True, with_meta=False):
        from nvesta.library.rb.registry import RefBookRegistry

        if edge:
            data = self.meta.edit or self.data
        else:
            data = self.data

        result = {}
        for description in self.rb.meta.fields:
            key = description.key
            value = data.get(key)
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

        if self._id:
            result['_id'] = str(self._id)

        if with_meta:
            _meta = self.meta.__json__()
            dirty = bool(_meta.pop('edit', False))
            result['_meta'] = dict(_meta, dirty=dirty)
        return result

    def __json__(self):
        return self.as_json(False)
