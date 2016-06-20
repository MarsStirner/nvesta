# -*- coding: utf-8 -*-
from flask import current_app, request
from nvesta.library.nsi.client import NsiClient
from pymongo import TEXT, ASCENDING

from hitsl_utils.api import api_method
from nvesta.api.app import module
from nvesta.library.nsi.data import create_indexes, kladr_set_parents, list_nsi_dictionaries, import_nsi_dict
from nvesta.systemwide import cache

__author__ = 'viruzzz-kun'


@module.route('/integrations/nsi/list/', methods=['GET'])
@api_method
def integrations_nsi_list():
    client = NsiClient(
        url=current_app.config.get('NSI_SOAP'),
        user_key=current_app.config.get('NSI_TOKEN'),
    )
    return list_nsi_dictionaries(client)


@module.route('/integrations/nsi/import/', methods=['POST'])
@api_method
def integrations_nsi_import():
    client = NsiClient(
        url=current_app.config.get('NSI_SOAP'),
        user_key=current_app.config.get('NSI_TOKEN'),
    )
    nsi_dict = request.get_json()
    result = import_nsi_dict(nsi_dict, client)
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
