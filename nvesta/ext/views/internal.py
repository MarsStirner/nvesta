# -*- coding: utf-8 -*-
from flask import request

from hitsl_utils.api import ApiException, api_method
from nvesta.ext.app import module
from nvesta.ext.library.ext_systems import ExtSystemProperties, ExtSystemCodeDuplicate
from nvesta.library.utils import bail_out

__author__ = 'viruzzz-kun'


@module.route('/api/v1/setup/', methods=['GET'])
@api_method
def ext_setup_list():
    return ExtSystemProperties.all()


@module.route('/api/v1/setup/', methods=['POST'])
@api_method
def ext_setup_new():
    prop = ExtSystemProperties()
    data = request.json
    if not data.get('code'):
        raise ApiException(400, u'Must have valid code')
    prop.update(data)
    try:
        prop.save()
    except ExtSystemCodeDuplicate:
        raise ApiException(400, 'Cannot insert External System with code %s. Code already used')
    return prop


@module.route('/api/v1/setup/<ext_system_code>', methods=['GET'])
@api_method
def ext_setup_item_get(ext_system_code):
    return ExtSystemProperties.find_by_code(ext_system_code) or bail_out(ApiException(404, '%s not found' % ext_system_code))


@module.route('/api/v1/setup/<ext_system_code>', methods=['PUT'])
@api_method
def ext_setup_item_put(ext_system_code):
    prop = ExtSystemProperties.find_by_code(ext_system_code) or bail_out(ApiException(404, '%s not found' % ext_system_code))
    prop.update(request.json)
    prop.save()
    return prop


@module.route('/api/v1/setup/<ext_system_code>', methods=['DELETE'])
@api_method
def ext_setup_item_del(ext_system_code):
    prop = ExtSystemProperties.find_by_code(ext_system_code) or bail_out(ApiException(404, '%s not found' % ext_system_code))
    prop.delete()
    raise ApiException(201, 'Success')
