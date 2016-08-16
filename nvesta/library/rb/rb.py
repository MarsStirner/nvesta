# -*- coding: utf-8 -*-
import datetime
from copy import copy

import bson

from nvesta.library.rb.classes import EdgeVersion, AnyVersion, DiffVersion, Undefined, CannotFixate

__author__ = 'viruzzz-kun'


class RefBook(object):
    """
    :type meta: nvesta.library.rb.rbmeta.RefBookMeta
    :type collection: pymongo.collection.Collection
    """
    meta = None
    collection = None
    record_factory = None

    def _update_kwargs_for_version(self, kwargs, version):
        if version is EdgeVersion:
            kwargs.update({
                '$or': [
                    {'_meta.end_version': None},
                    {'_meta.draft': True}
                ]
            })
        elif version is None or version == self.meta.version:
            kwargs.update({
                '$or': [
                    {'_meta.end_version': self.meta.version},
                    {'$and': [
                        {'_meta.end_version': None},
                        {'_meta.draft': False}
                    ]}
                ]
            })
        elif version is AnyVersion:
            pass
        elif version is DiffVersion:
            kwargs.update({
                '$and': [
                    {'_meta.end_version': None},
                    {'$or': [
                        {'_meta.draft': {'$ne': False}},
                        {'_meta.delete': {'$ne': False}},
                        {'_meta.edit': {'$ne': None}},
                    ]},
                ]
            })
        else:
            kwargs.update({
                '$and': [
                    {'_meta.beg_version': {'$lte': version}},
                    {'$or': [
                        {'_meta.end_version': {'$gte': version}},
                        {'$and': [
                            {'_meta.end_version': None},
                            {'_meta.draft': {'$ne': True}},
                        ]},
                    ]},
                ]
            })
            # kwargs['_meta.draft'] = False

    def find(self, kwargs, sort=None, limit=None, skip=None, version=None):
        """
        Извлечение списка записей по заданным параметрам
        @param kwargs: параметры для pymongo.collection.Collection.find
        @param sort: параметр для pymongo.cursor.Cursor.sort
        @param limit: параметр для pymongo.cursor.Cursor.limit
        @param skip: параметр для pymongo.cursor.Cursor.skip
        @param version: ограничить записи определённой версией
        @type kwargs: dict
        @type sort: dict|str
        @type limit: int|None
        @type skip: int|None
        @type version: int|str|None|DiffVersion|AnyVersion|EdgeVersion
        @return:
        """
        kwargs = copy(kwargs)
        self._update_kwargs_for_version(kwargs, version)

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

    def find_one(self, kwargs, rec_id=Undefined, version=None):
        """
        Извлечение одной записи из справочника
        @param kwargs: условия выборки или имя поля
        @param rec_id: значение поля, если kwargs - имя поля
        @param version: версия, для которой запись тянуть
        @type kwargs: dict | str
        @type rec_id: * | Undefined
        @type version: int|str|None|DiffVersion|AnyVersion|EdgeVersion
        @return: Запись из справочника
        @rtype: nvesta.library.rbrecord.RefBookRecord
        """
        if rec_id is not Undefined:
            if kwargs == '_id' and isinstance(rec_id, basestring):
                rec_id = bson.ObjectId(rec_id)
            kwargs = {kwargs: rec_id}
        self._update_kwargs_for_version(kwargs, version)
        result = self.collection.find_one(kwargs)
        return self.record_factory(result)

    def save(self, rb_record):
        """
        Сохранение записи в справочнике
        @type rb_record: nvesta.library.rbrecord.RefBookRecord
        @param rb_record: Запись
        @return: Запись
        @rtype: nvesta.library.rbrecord.RefBookRecord
        """
        data = rb_record.as_db_record(with_id=True)
        _id = data.pop('_id', Undefined)
        if _id is not Undefined:
            if rb_record.meta.draft and rb_record.meta.delete:
                self.collection.delete_one({'_id': _id})
                rb_record._id = None
            else:
                self.collection.update_one(
                    {'_id': _id},
                    {'$set': data}
                )
        else:
            result = self.collection.insert_one(data)
            rb_record._id = result.inserted_id
        return rb_record

    def save_bulk(self, rb_records):
        """
        Массовое сохранение записей
        @param rb_records: Список записей
        @type rb_records: list<RefBookRecord>
        @return: None
        """
        from pymongo import InsertOne, UpdateOne

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
        requests = [make_request(copy(rb_record.as_db_record())) for rb_record in rb_records]
        self.collection.bulk_write(requests)

    def delete_record(self, rb_record):
        """
        Физическое удаление записи
        @param rb_record: Запись
        @type rb_record: nvesta.library.rbrecord.RefBookRecord
        @return:
        """
        if rb_record._id:
            self.collection.delete_one({'_id': rb_record._id})

    def fixate(self, new_version):
        """
        Фиксация изменений
        @return:
        """
        if new_version == self.meta.version:
            raise CannotFixate('New version equals current version')
        if new_version in [v.version for v in self.meta.versions]:
            raise CannotFixate('New version already present in previous versions')

        from pymongo import InsertOne, UpdateOne, DeleteMany, UpdateMany
        from nvesta.library.rb.rbrecord import RefBookRecordMeta

        old_version = self.meta.version or new_version

        # noinspection PyListCreation
        requests = []

        # Если справочник был неверсионным и у нас записи без меты, надо забить её умолчаниями.
        requests.append(
            UpdateMany(
                {'_meta': None},
                {'$set': {'_meta': RefBookRecordMeta.from_rb_meta(self.meta).as_db_record()}},
            )
        )

        # Новые удалённые - просто удаляем
        requests.append(
            DeleteMany({'$and': [
                {'_meta.delete': True},
                {'_meta.draft': True}
            ]}))

        # Старые удалённые - помечаем конечной версией
        for db_record in self.collection.find({'$and': [
            {'_meta.delete': True},
            {'_meta.draft': False}
        ]}):
            rb_record = self.record_factory(db_record)
            rb_record.meta.delete = False
            rb_record.meta.draft = False
            rb_record.meta.edit = None
            rb_record.meta.end_version = old_version
            requests.append(UpdateOne(
                {'_id': rb_record._id},
                {'$set': rb_record.as_db_record()},
            ))

        # Новые записи - помечаем начальной версией
        for db_record in self.collection.find({'$and': [
            {'_meta.delete': False},
            {'_meta.draft': True},
        ]}):
            rb_record = self.record_factory(db_record)
            rb_record.meta.draft = False
            rb_record.meta.delete = False
            rb_record.meta.end_version = None
            rb_record.meta.beg_version = new_version
            requests.append(UpdateOne(
                {'_id': rb_record._id},
                {'$set': rb_record.as_db_record()},
            ))

        # Изменённые - создаём новую, а старую помечаем конечной версией
        for db_record in self.collection.find({'_meta.edit': {'$ne': None}}):
            rb_record = self.record_factory(db_record)

            new = self.record_factory(rb_record.meta.edit)
            new.meta.beg_version = new_version
            new.meta.end_version = None
            new.meta.delete = False
            new.meta.draft = False
            requests.append(InsertOne(new.as_db_record()))

            rb_record.meta.end_version = old_version
            rb_record.meta.edit = None
            rb_record.meta.delete = False
            rb_record.meta.draft = False
            requests.append(UpdateOne(
                {'_id': rb_record._id},
                {'$set': rb_record.as_db_record()},
            ))

        self.collection.bulk_write(requests)
        self.meta.version = new_version

        from nvesta.library.rb.rbmeta import RefBookVersionMeta

        version_meta = RefBookVersionMeta()
        version_meta.version = new_version
        version_meta.fix_datetime = datetime.datetime.utcnow()
        self.meta.versions.append(version_meta)
        self.meta.reshape()

    def ensure_default_indexes(self):
        """
        Создание индексов для полей, считающихся в справочнике ключами
        @return:
        """
        all_names = set(field.key for field in self.meta.fields)
        key_names = (key for key in ('identcode', 'code', 'id', 'recid', 'oid') if key in all_names)
        for name in key_names:
            self.collection.create_index(name, sparse=True)

    def get_primary_linked_rb(self):
        """
        Получение справочника по первичной связке
        @return: Справочник
        @rtype: RefBook | NoneType
        """
        if self.meta.primary_link.right_rb_code:
            from nvesta.library.rb.registry import RefBookRegistry

            return RefBookRegistry.get(self.meta.primary_link.right_rb_code)