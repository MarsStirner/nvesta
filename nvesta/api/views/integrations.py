# -*- coding: utf-8 -*-
from flask import current_app, request
from nvesta.library.nsi.client import NsiClient

from hitsl_utils.api import api_method
from nvesta.api.app import module
from nvesta.library.nsi.data import kladr_maintenance, list_nsi_dictionaries, import_nsi_dict

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
    return result


@module.route('/integrations/nsi/utils/kladr/', methods=['POST'])
@api_method
def integrations_import_nsi():
    kladr_maintenance()
