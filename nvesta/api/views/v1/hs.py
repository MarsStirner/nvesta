# -*- coding: utf-8 -*-

from flask import request

from hitsl_utils.api import ApiException
from nvesta.api.app import module
from nvesta.api.views.v1.apiutils import core_api_method
from nvesta.library.rb.registry import RefBookRegistry
from nvesta.library.utils import force_json, prepare_find_params

nsi_name_keys = ('name', 'name_short', 'descr', 'res_descr', 'mkb_name')


def _prepare_hs_response(data, dict_code):
    """
    :type data: nvesta.library.rbrecord.RefBookRecord
    :param data:
    :param dict_code:
    :return:
    """
    data = data.data
    return_data = dict()
    if 'unq' in data:
        return_data['code'] = data['unq']
    elif 'mkb_code' in data:
        return_data['code'] = data['mkb_code']
    elif 'code' in data:
        return_data['code'] = data['code']
    elif 'id' in data:
        return_data['code'] = data['id']
    elif 'recid' in data:
        return_data['code'] = data['recid']

    for key in nsi_name_keys:
        if key in data:
            return_data['name'] = data[key]
            break

    # Для rbSocStatusType и MDN366 в поле code проставляется значение из id
    if dict_code in ('rbSocStatusType', 'MDN366'):
        return_data['code'] = data['id']
    return return_data


@module.route('/hs/<code>/<field>/<field_value>/', methods=['GET'])
@core_api_method
def get_data_hs(code, field, field_value):
    rb = RefBookRegistry.get(code)
    find = {field: field_value}
    doc = rb.find_one(find)
    if rb.meta.oid:
        # Работаем с НСИ справочником
        data = doc
        oid = rb.meta.oid
    else:
        # Переключаемся на НСИ справочник
        link_meta = rb.meta.primary_link
        linked_rb = rb.get_primary_linked_rb()
        if not linked_rb or not linked_rb.meta.oid:
            raise ApiException(404, u'Нет связанного справочника НСИ')
        data = linked_rb.find_one({
            link_meta.right_field: doc[link_meta.left_field]
        })
        oid = linked_rb.meta.oid
    if data:
        data = _prepare_hs_response(data, code)
    else:
        data = {}
    return {
        'oid': oid,
        'data': data,
    }


@module.route('/hs/<code>/', methods=['POST'])
@core_api_method
def find_data_hs(code):
    data = force_json(request)

    rb = RefBookRegistry.get(code)

    ret_data = rb.meta.__json__()
    ret_data['data'] = rb.find_one(prepare_find_params(data))
    return ret_data
