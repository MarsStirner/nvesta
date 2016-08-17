# -*- coding: utf-8 -*-
import bson
from flask import request

from hitsl_utils.api import ApiException, crossdomain
from nvesta.api.app import module
from nvesta.api.views.v1.apiutils import v1_api_method
from nvesta.library.rb.registry import RefBookRegistry
from nvesta.library.utils import prepare_find_params, force_json

"""API для работы с конкретным справочником"""

base_url = '/v1/<string:code>/'


@module.route('/v1/<rb_code>/', methods=['GET'])
@crossdomain('*', methods=['GET'])
@v1_api_method
def v1_dictionary_list(rb_code):
    rb = RefBookRegistry.get(rb_code)
    if not rb:
        raise ApiException(404, 'Dictionary not found')
    return rb.find({})


@module.route('/v1/<rb_code>/<doc_id>', methods=['GET'])
@crossdomain('*', methods=['GET'])
@v1_api_method
def v1_dictionary_get_document(rb_code, doc_id):
    rb = RefBookRegistry.get(rb_code)
    return rb.find('_id', doc_id)


@module.route('/v1/<rb_code>/<field>/<value>/', methods=['GET'])
@crossdomain('*', methods=['GET'])
@v1_api_method
def v1_get_document_by_field(rb_code, field, value):
    if field == 'id':
        value = int(value)
    elif field == '_id':
        value = bson.ObjectId(value)
    rb = RefBookRegistry.get(rb_code)
    return rb.find_one(field, value)


@module.route('/v1/<rb_code>/', methods=['POST'])
@crossdomain('*', methods=['POST'])
@v1_api_method
def v1_dictionary_post(rb_code):
    data = force_json(request)
    rb = RefBookRegistry.get(rb_code)
    if isinstance(data, list):
        id_list = []
        for doc in data:
            record = rb.record_factory(doc)
            rb.save(record)
            id_list.append(record.data.get('_id'))
        return {'_id': id_list}
    record = rb.record_factory(data)
    rb.save(record)
    return {'_id': record.data.get('_id')}


@module.route('/v1/<rb_code>/<document_id>/', methods=['PUT'])
@crossdomain('*', methods=['PUT'])
@v1_api_method
def dictionary_put(rb_code, document_id):
    data = force_json(request)
    rb = RefBookRegistry.get(rb_code)
    data['_id'] = bson.ObjectId(document_id)
    record = rb.record_factory(data)
    rb.save(record)
    return document_id


@module.route('/v1/rb_code/<document_id>/', methods=['DELETE'])
@crossdomain('*', methods=['DELETE'])
@v1_api_method
def dictionary_delete(rb_code, document_id):
    raise NotImplemented


# TODO: По возможности отказаться от хвоста или хотя бы сменить ему имя
@module.route('/v1/find/<code>/', methods=['POST'])
@module.route('/find/<code>/', methods=['POST'])
@crossdomain('*', methods=['POST'])
@v1_api_method
def find_data(code):
    data = force_json(request)
    rb = RefBookRegistry.get(code)
    find = prepare_find_params(data)
    return rb.find(find)
