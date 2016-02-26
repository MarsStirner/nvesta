# -*- coding: utf-8 -*-
import contextlib
import logging
from datetime import datetime

import itertools

from nvesta.library.shape import RefBookRegistry
from nvesta.systemwide import app
from .client import NsiClient

logger = logging.getLogger('simple')
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
# logging.getLogger('suds.bindings.multiref').addHandler(logging.StreamHandler())

def format_key(_key):
    _key = _key.lower()
    prefixes = ['s_', 'n_', 'v_']
    for prefix in prefixes:
        if _key.startswith(prefix):
            _key = _key.replace(prefix, '')
    return str(_key)


def prepare_dictionary(data):
    return {
        format_key(field.key): field.value
        for field in getattr(getattr(data, 'children', []), 'item', [])
    }


class LogMsg(object):
    def __init__(self, tags=None):
        self.tags = set(tags) if tags is not None else set()
        self._level = logging.DEBUG
        self._list = []

    def log(self, message):
        self._list.append(message)

    def error(self, message):
        self._list.append(message)
        self._level = logging.ERROR

    def finish(self):
        compose = u'\n'.join(self._list)
        extra={'tags': sorted(self.tags)}
        if self._level == logging.ERROR:
            logger.error(compose, extra=extra)
        else:
            logger.debug(compose, extra=extra)


@contextlib.contextmanager
def log_context(tags=None):
    lm = LogMsg(tags)
    yield lm
    lm.finish()


def list_nsi_dictionaries():
    client = NsiClient(
        url=app.config.get('NSI_SOAP'),
        user_key=app.config.get('NSI_TOKEN'),
    )

    result = client.getRefbookList() or []
    final = []
    for nsi_dict_raw in result:
        nsi_dict = prepare_dictionary(nsi_dict_raw)
        code = nsi_dict['code']
        try:
            # Пытаемся понять, какая версия справочника нынче актуальна
            nsi_dict['version'] = prepare_dictionary(client.getVersionList(code)[-1])['version']
        except (IndexError, ValueError):
            continue
        try:
            rb = RefBookRegistry.get(code)
        except KeyError:
            rb = None
        final.append({
            'their': nsi_dict,
            'our': rb.meta,
        })
    return final


def import_nsi_dict(nsi_dict):
    client = NsiClient(
        url=app.config.get('NSI_SOAP'),
        user_key=app.config.get('NSI_TOKEN'),
    )
    code = nsi_dict['code']
    name = nsi_dict['name']

    with log_context(['nsi', 'import']) as log:
        log.log(u'Импорт {0} ({1})'.format(name, code))
        log.tags.add(code)

        try:
            # Пытаемся понять, какая версия справочника нынче актуальна
            latest_version = prepare_dictionary(client.getVersionList(code)[-1])
            latest_version['date'] = datetime.strptime(latest_version['date'], '%d.%m.%Y')
        except (IndexError, ValueError), e:
            # Не получилось. С позором ретируемся.
            log.tags.add('import error')
            log.error(u'Ошибка получения версии ({0}): {1}'.format(code, e))
            return

        try:
            # Есть два варианта: либо справочник есть...
            rb = RefBookRegistry.get(code)
        except KeyError:
            # ...либо его надо создать.
            rb = RefBookRegistry.create({
                'code': nsi_dict.get('code', nsi_dict.get('id')),
                'name': nsi_dict.get('name', nsi_dict.get('code', nsi_dict.get('id'))),
                'description': nsi_dict.get('description'),
                'oid': nsi_dict.get('oid'),
            })

        my_version = rb.meta.version
        their_version = latest_version['version']
        documents = []
        if not my_version:
            log.log(u'Локальный справочник не имеет версии, создаётся')
            documents = [
                prepare_dictionary(document)
                for i in xrange(client.get_parts_number(code, their_version) or 0)
                for document in itertools.ifilter(None, client.get_parts_data(code, their_version, i + 1))
                ]
        elif my_version and my_version != their_version:
            log.log(u'Локальная версия справочника: {0}'.format(my_version))
            log.log(u'Актуальная версия справочника: {0}'.format(latest_version))
            log.log(u'Версии не совпадают, обновляем diff')
            documents = [
                prepare_dictionary(document)
                for document in itertools.ifilter(None, client.getRefbookUpdate(code=code, user_version=my_version))
                ]
        else:
            log.log(u'Локальная версия справочника: {0}'.format(my_version))
            log.log(u'Актуальная версия справочника: {0}'.format(latest_version))
            log.log(u'Версии совпадают, не обновляем справочник')

        if documents:
            # Есть, что обновлять
            # Сперва меняем (при необходимости) структуру справочника
            names = set()
            for doc in documents:
                names.update(set(doc.iterkeys()))
            new_names = names - set(field['key'] for field in rb.meta.fields)
            if new_names:
                # Новые столбцы появились, надо добавить
                for name in new_names:
                    rb.meta.fields.append({
                        'key': name,
                        'type': 'string',
                        'mandatory': False,
                        'unique': False,
                        'link': None,
                    })
                rb.meta.reshape()

            for doc in documents:
                existing = None
                for key in ['code', 'id', 'recid', 'oid']:
                    if key in doc:
                        existing = rb.find_one({key: doc[key]})
                if not existing:
                    existing = rb.record_factory()
                existing.update(doc)
                # existing['code'] = doc.get('code', doc['id'])
                rb.save(existing)
            rb.meta.version = their_version
            rb.meta.reshape()
            log.log(u'Справочник ({0}) обновлён'.format(code))


def create_indexes(collection_indexes):
    if not isinstance(collection_indexes, dict):
        return None
    for code, indexes in collection_indexes.items():
        rb = RefBookRegistry.get(code)
        if not isinstance(indexes, list):
            indexes = [indexes]
        for index in indexes:
            for field, index_type in index.items():
                rb.collection.ensure_index(field, index_type)


def kladr_set_parents():
    rb = RefBookRegistry.get('KLD172')
    limit = 1000
    for i in xrange(0, 300):
        documents = rb.find({'identparent': {'$ne': None}}, limit=limit, skip=i*limit)
        if not documents:
            break
        for document in documents:
            parent = rb.find_one({'identcode': document['identparent']})
            rb.collection.update_one({'_id': document.id}, {'parent': {'$set': parent['_id'] if parent else None}})