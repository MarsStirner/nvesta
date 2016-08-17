# -*- coding: utf-8 -*-
from flask import request

from hitsl_utils.api import api_method, ApiException
from nvesta.ext.app import module
from nvesta.ext.library.ext_systems import ExtSystemProperties
from nvesta.library.utils import bail_out

__author__ = 'viruzzz-kun'


@module.route('/api/v1/rb/<ext_sys_code>/', methods=['GET'])
@api_method
def api_ext_get_dict_list(ext_sys_code):
    props = ExtSystemProperties.find_by_code(ext_sys_code) or bail_out(ApiException(404, 'Integration not found'))
    return props.refbooks_metas


@module.route('/api/v1/rb/<ext_sys_code>/<rb_code>/meta/', methods=['GET'])
@api_method
def api_ext_get_dict_meta(ext_sys_code, rb_code):
    props = ExtSystemProperties.find_by_code(ext_sys_code) or bail_out(ApiException(404, 'Integration not found'))
    refbooks_dict = props.refbooks_dict
    if rb_code not in refbooks_dict:
        raise ApiException(404, '"%s" not found for integration "%s"' % (rb_code, ext_sys_code))
    return refbooks_dict[rb_code].meta


@module.route('/api/v1/rb/<ext_sys_code>/<rb_code>/data/', methods=['GET'])
@api_method
def api_ext_get_dict_data(ext_sys_code, rb_code):
    props = ExtSystemProperties.find_by_code(ext_sys_code) or bail_out(ApiException(404, 'Integration not found'))
    version = request.args.get('version', None)
    refbooks_dict = props.refbooks_dict
    if rb_code not in refbooks_dict:
        raise ApiException(404, '"%s" not found for integration "%s"' % (rb_code, ext_sys_code))
    return refbooks_dict[rb_code].find({}, version=version)


@module.route('/api/v1/rb/<ext_sys_code>/<rb_code>/data/<field>/<rec_id>/', methods=['GET'])
@api_method
def api_ext_get_dict_item(ext_sys_code, rb_code, field, rec_id):
    props = ExtSystemProperties.find_by_code(ext_sys_code) or bail_out(ApiException(404, 'Integration not found'))
    version = request.args.get('version', None)
    refbooks_dict = props.refbooks_dict
    if rb_code not in refbooks_dict:
        raise ApiException(404, '"%s" not found for integration "%s"' % (rb_code, ext_sys_code))
    return refbooks_dict[rb_code].find(field, rec_id, version=version)

