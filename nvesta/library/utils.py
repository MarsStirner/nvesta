# -*- coding: utf-8 -*-
import json
import re

from hitsl_utils.api import ApiException

__author__ = 'viruzzz-kun'


def prepare_find_params(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) or isinstance(value, unicode):
                data[key] = re.compile(value, re.IGNORECASE)
    elif isinstance(data, str) or isinstance(data, unicode):
        data = re.compile(data, re.IGNORECASE)
    return data


def force_json(_request):
    data = _request.get_json()
    if not data:
        data = json.loads(_request.data)
    if not data:
        raise ApiException(400, u'Не переданы данные, или переданы неверным методом')
    return data


