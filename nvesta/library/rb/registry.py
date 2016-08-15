# -*- coding: utf-8 -*-
import logging

import pymongo.database

from nvesta.library.rb.rb import RefBook
from nvesta.library.rb.rbmeta import RefBookMeta
from nvesta.library.rb.rbrecord import RefBookRecordMeta, RefBookRecord
from nvesta.library.utils import bail_out

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


class RefBookRegistry(object):
    """
    Реестр справочников.
    """
    ref_books = {}
    db = None

    @classmethod
    def refbook_from_meta(cls, meta):
        """
        Внутренний метод для создания объекта справочника по метаданным
        @param meta: метаданные
        @type meta: nvesta.library.refbook.RefBookMeta
        @return: Справочник
        @rtype: nvesta.library.refbook.RefBook
        """
        refbook = RefBook()
        refbook.meta = meta
        refbook.collection = cls.db['refbook.%s' % meta.code]
        refbook.record_factory = RefBookRecord.for_refbook(refbook)
        cls.ref_books[meta.code] = refbook

        return refbook

    @classmethod
    def get(cls, code):
        """
        Получение справочника по его коду
        @param code: Код справочника
        @type code: str
        @return: Справочник
        @rtype: RefBook
        @raise KeyError: Нет справочника с таким кодом
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
        """
        Создание справочника по метаданным (в сыром виде - как в БД или с фронтенда)
        @param raw_meta: Метаданные (сырые)
        @type raw_meta: dict
        @return: Справочник
        @rtype: RefBook
        @raise ValueError: Справочник уже создан
        """
        cls.db['refbooks'].find_one({'code': raw_meta['code']}) and bail_out(ValueError(raw_meta['code']))
        raw_meta.pop('_id', None)
        meta = RefBookMeta.from_db_record(raw_meta)
        meta.id = cls.db['refbooks'].insert(meta.as_db_record())
        cls.db.create_collection('refbook.%s' % meta.code)
        meta.reshape()
        return cls.refbook_from_meta(meta)

    @classmethod
    def names(cls):
        """
        Получение кодов всех справочников
        @return: Список кодов справочников
        @rtype: list<str>
        """
        return [description['code'] for description in cls.db['refbooks'].find()]

    @classmethod
    def list(cls):
        """
        Получение списка всех справочников. Параллельно загружает все объекты справочников в кеш (метаданные, не данные)
        @return: Справочники
        @rtype: list<RefBook>
        """
        names = cls.db['refbooks'].find()
        return [
            cls.get(description['code'])
            for description in names
        ]

    @classmethod
    def bootstrap(cls, mongo_db):
        """
        Инициализация реестра справочников - подключение БД Mongo
        @param mongo_db: объект БД Mongo
        @type mongo_db: flask_pymongo.wrappers.Database | pymongo.database.Database
        @return:
        """
        cls.db = mongo_db
        run = True
        try:
            import uwsgi
            run = uwsgi.worker_id() == 0
        except ImportError:
            pass

        if run:
            cls.bootstrap_refbooks()
            try:
                cls.db.create_collection('vesta.meta')
            except pymongo.database.CollectionInvalid:
                return
            else:
                collection = cls.db['vesta.meta']
                collection.update_one(
                    {'version': '0.2'},
                    {'version': '0.2'},
                    True
                )

    @classmethod
    def bootstrap_refbooks(cls):
        collection_names = cls.db.collection_names(False)
        if 'refbooks' not in collection_names:
            cls.db.create_collection('refbooks')
        for rb in cls.list():
            logger.info('Bootstrapping %s ...', rb.meta.code)
            rb.ensure_default_indexes()
            default_meta = RefBookRecordMeta.from_rb_meta(rb.meta).as_db_record()
            rb.collection.update_many(
                {'_meta': None},
                {'$set': {'_meta': default_meta}},
            )

    @classmethod
    def invalidate(cls, code=None):
        """
        Выбрасывание одного или нескольких
        @param code:
        @return:
        """
        if code is not None:
            cls.ref_books.pop(code, None)
        else:
            cls.ref_books.clear()
