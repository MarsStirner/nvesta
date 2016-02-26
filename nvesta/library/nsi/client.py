# -*- coding: utf-8 -*-
import logging
from suds.client import Client
from suds import WebFault

from . import exc

logger = logging.getLogger('simple')


class NsiClient(object):
    """Класс SOAP-клиента для взаимодействия со сервисом НСИ"""
    def __init__(self, url, user_key):
        self.user_key = user_key
        self.client = Client(url, cache=None)

    def __get_error(self, result):
        # TODO: отрефакторить и вынести в NSIResult.get_errors, соответственно создать класс-обертку для результатов
        try:
            first = result[0]
        except IndexError, e:
            pass
        else:
            if first.key == 'errors':
                errors = dict()
                children = getattr(first, 'children', None)
                if children:
                    for child in getattr(children, 'item', []):
                        errors[child.key] = child.value
                    return errors
        return None

    def get_refbook_data(self, code, version):
        result = self.getRefbook(code, version)
        errors = self.__get_error(result)
        if errors and exc.RefbookTooLargeError.code in errors:
            # Получаем количество частей и выкачиваем справочник по частям
            parts = self.getRefbookParts(code, version)
            parts_number = int(parts[0].value)
            if parts_number:
                result = list()
                for i in xrange(1, parts_number + 1):
                    part_data = self.getRefbookPartial(code, version, i)
                    result.extend(part_data)
        return result

    def get_parts_number(self, code, version):
        # Получаем количество частей
        parts = self.getRefbookParts(code, version)
        parts_number = int(parts[0].value)
        return parts_number

    def get_parts_data(self, code, version, number):
        # Получаем количество частей
        part_data = self.getRefbookPartial(code, version, number)
        return part_data

    def getRefbook(self, code, version):
        try:
            result = self.client.service.getRefbook(userKey=self.user_key,
                                                    refbookCode=str(code),
                                                    version=str(version))
        except WebFault, e:
            print e
            logger.error(e, extra=dict(tags=['getRefbook', 'nsi']))
        else:
            return getattr(result, 'item', [])
        return None

    def getRefbookList(self):
        try:
            result = self.client.service.getRefbookList(userKey1=self.user_key)
        except WebFault, e:
            print e
            logger.error(e, extra=dict(tags=['getRefbookList', 'nsi']))
        else:
            return getattr(result, 'item', [])
        return None

    def getRefbookPartial(self, code, version, part_number):
        try:
            result = self.client.service.getRefbookPartial(userKey2=self.user_key,
                                                           refbookCode1=code,
                                                           version1=version,
                                                           partNumber=part_number)
        except WebFault, e:
            print e
            logger.error(e, extra=dict(tags=['getRefbookPartial', 'nsi']))
        else:
            return getattr(result, 'item', [])
        return None

    def getRefbookParts(self, code, version):
        try:
            result = self.client.service.getRefbookParts(userKey3=self.user_key,
                                                         refbookCode2=code,
                                                         version2=version)
        except WebFault, e:
            print e
            logger.error(e, extra=dict(tags=['getRefbookParts', 'nsi']))
        else:
            return getattr(result, 'item', [])
        return None

    def getRefbookUpdate(self, code, user_version=None, new_version=None):
        try:
            parameters = dict(userKey4=self.user_key, refbookCode3=code)
            if user_version is not None:
                parameters['userVersion'] = user_version
            if new_version is not None:
                parameters['newVersion'] = new_version
            result = self.client.service.getRefbookUpdate(**parameters)
        except WebFault, e:
            print e
            logger.error(e, extra=dict(tags=['getRefbookUpdate', 'nsi']))
        else:
            return getattr(result, 'item', [])
        return None

    def getServerTime(self):
        try:
            result = self.client.service.getServerTime()
        except WebFault, e:
            print e
            logger.error(e, extra=dict(tags=['getServerTime', 'nsi']))
        else:
            return result
        return None

    def getVersionList(self, code):
        try:
            result = self.client.service.getVersionList(userKey5=self.user_key, refbookCode4=code)
        except WebFault, e:
            print e
            logger.error(e, extra=dict(tags=['getVersionList', 'nsi']))
        else:
            return getattr(result, 'item', [])
        return None