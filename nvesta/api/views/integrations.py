# -*- coding: utf-8 -*-
import flask
from pymongo import TEXT, ASCENDING

from hitsl_utils.api import api_method
from nvesta.api.app import module
from nvesta.library.nsi.data import create_indexes, kladr_set_parents, list_nsi_dictionaries, import_nsi_dict
from nvesta.systemwide import cache

__author__ = 'viruzzz-kun'


@module.route('/integrations/nsi/list/', methods=['GET'])
@api_method
@cache.memoize(3600)
def integrations_nsi_list():
    return list_nsi_dictionaries()


@module.route('/integrations/nsi/import/', methods=['POST'])
@api_method
def integrations_nsi_import():
    nsi_dict = flask.request.get_json()
    result = import_nsi_dict(nsi_dict)
    cache.delete_memoized(integrations_nsi_list)
    return result


@module.route('/integrations/nsi/utils/kladr/', methods=['POST'])
@api_method
def integrations_import_nsi():
    create_indexes({
        'KLD172': [{'name': TEXT, 'level': ASCENDING}, {'identcode': ASCENDING}],
        'STR172': [{'name': TEXT}, {'identcode': ASCENDING}, {'identparent': ASCENDING}]
    })
    kladr_set_parents()
