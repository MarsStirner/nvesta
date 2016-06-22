# -*- coding: utf-8 -*-
import contextlib
import logging
from datetime import datetime

from pymongo import ASCENDING

from hitsl_utils.api import ApiException
from nvesta.library.shape import RefBookRegistry

logger = logging.getLogger('simple')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

stream_logger = logging.getLogger('NsiImportStreamLogger')
stream_logger.setLevel(logging.DEBUG)
stream_logger.addHandler(handler)
stream_formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(stream_formatter)


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
        stream_logger.debug('Entering logging context %s.' % ('with tags %s' % ', '.join(set(tags) if tags else 'without tags')))
        self.tags = set(tags) if tags is not None else set()
        self._level = logging.DEBUG
        self._list = []

    def log(self, message):
        stream_logger.info(message)
        self._list.append(message)

    def error(self, message):
        stream_logger.error(message)
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


def list_nsi_dictionaries(nsi_client):
    result = nsi_client.getRefbookList() or []
    final = []
    for nsi_dict_raw in result:
        if nsi_dict_raw.key == 'errors':
            raise ApiException(
                500,
                u'Ошибка доступа к НСИ:\n%s' % (u'\n'.join(
                    u'%s: %s' % (item.key, item.value)
                    for item in nsi_dict_raw.children[0]
                ))
            )
        nsi_dict = prepare_dictionary(nsi_dict_raw)
        code = nsi_dict['code']
        try:
            # Пытаемся понять, какая версия справочника нынче актуальна
            nsi_dict['version'] = prepare_dictionary(nsi_client.getVersionList(code)[-1])['version']
        except (IndexError, ValueError):
            continue
        meta = None
        try:
            rb = RefBookRegistry.get(code)
            meta = rb.meta
        except KeyError:
            pass
        final.append({
            'their': nsi_dict,
            'our': meta,
        })
    return final


def import_nsi_dict(nsi_dict, nsi_client):
    code = nsi_dict['code']
    name = nsi_dict['name']

    with log_context(['nsi', 'import']) as log:
        log.log(u'Импорт {0} ({1})'.format(name, code))
        log.tags.add(code)

        try:
            # Пытаемся понять, какая версия справочника нынче актуальна
            latest_version = prepare_dictionary(nsi_client.getVersionList(code)[-1])
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

        def dump_documents(docs):
            log.log(u'Начинаем обновление данных...')
            documents = map(prepare_dictionary, docs)
            log.log(u'Новых/изменённых записей: %s' % len(documents))
            # Сперва меняем (при необходимости) структуру справочника
            names = set()
            for doc in documents:
                names.update(set(doc.iterkeys()))
            own_names = set(field['key'] for field in rb.meta.fields)
            new_names = names - own_names
            all_names = names | own_names
            if new_names:
                # Новые столбцы появились, надо добавить
                log.log(u'Структура справочника изменилась. Решейпим...')
                for key in new_names:
                    rb.meta.fields.append({
                        'key': key,
                        'type': 'string',
                        'mandatory': False,
                        'unique': False,
                        'link': None,
                    })
                rb.meta.reshape()

            key_names = (key for key in ('code', 'id', 'recid', 'oid') if key in all_names)
            for key in key_names:
                rb.collection.create_index(key, sparse=True)

            log.log(u'Добавляем/обновляем записи...')
            documents_to_save = []
            for doc in documents:
                existing = None
                for key in key_names:
                    if key in doc:
                        existing = rb.find_one({key: doc[key]})
                if not existing:
                    existing = rb.record_factory()
                existing.update(doc)
                documents_to_save.append(existing)
            log.log(u'Сбрасываем записи в БД...')
            rb.save_bulk(documents_to_save)

        if not my_version:
            log.log(u'Локальный справочник не имеет версии, создаётся')
            parts_number = nsi_client.get_parts_number(code, their_version)
            log.log(u'Ответ получен. Всего частей: %s' % parts_number)
            for i in xrange(parts_number or 0):
                log.log(u'Запрашиваем часть %s / %s' % (i + 1, parts_number))
                request_result = nsi_client.get_parts_data(code, their_version, i + 1)
                log.log(u'Ответ получен. Разбираем...')
                dump_documents(doc for doc in request_result if doc)
            log.log(u'Разобрано')
        elif my_version and my_version != their_version:
            log.log(u'Локальная версия справочника: {0}'.format(my_version))
            log.log(u'Актуальная версия справочника: {0}'.format(their_version))
            log.log(u'Версии не совпадают, обновляем diff...')
            request_result = nsi_client.getRefbookUpdate(code=code, user_version=my_version)
            log.log(u'Ответ получен. Разбираем...')
            dump_documents(doc for doc in request_result if doc)
            log.log(u'Разобрано')
        else:
            log.log(u'Локальная версия справочника: {0}'.format(my_version))
            log.log(u'Актуальная версия справочника: {0}'.format(their_version))
            log.log(u'Версии совпадают, не обновляем справочник')
            return

    rb.meta.version = their_version
    rb.meta.reshape()
    log.log(u'Справочник ({0}) обновлён'.format(code))


def kladr_maintenance():
    with log_context(['kladr', 'maintenance']) as log:
        log.log(u'Проверяем индексы на справочнике STR172 (улицы)')
        rb = RefBookRegistry.get('STR172')
        log.log(u'   name')
        rb.collection.create_index([('name', ASCENDING)])
        log.log(u'   identcode')
        rb.collection.create_index([('identcode', ASCENDING)])
        log.log(u'   identparent')
        rb.collection.create_index([('identparent', ASCENDING)])

        log.log(u'Проверяем индексы на справочнике KLD172 (регионы)')
        rb = RefBookRegistry.get('KLD172')
        log.log(u'   name + level')
        rb.collection.create_index([('name', ASCENDING), ('level', ASCENDING)])
        log.log(u'   identparent')
        rb.collection.create_index([('identcode', ASCENDING)])
