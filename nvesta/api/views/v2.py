# -*- coding: utf-8 -*-
import bson
import flask

from hitsl_utils.api import api_method, ApiException
from nvesta.api.app import module
from nvesta.library.shape import RefBookRegistry

__author__ = 'viruzzz-kun'


@module.route('/v2/rb/', methods=['GET'])
@api_method
def rb_list_get():
    """
    Список всех имеющихся справочников
    :return:
    """
    rb_list = RefBookRegistry.list()
    result = [
        d.meta
        for d in rb_list
    ]
    result.sort(key=lambda meta: meta.code)
    return result


@module.route('/v2/rb/', methods=['POST'])
@api_method
def rb_post():
    """
    Создание нового справочника
    :return:
    """
    j = flask.request.get_json()
    rb = RefBookRegistry.create(j['code'], j['name'])
    return rb.meta


@module.route('/v2/rb/<rb_code>/meta/', methods=['GET'])
@api_method
def rb_get(rb_code):
    """
    Получение метаданных справочника
    :param rb_code:
    :return:
    """
    rb = RefBookRegistry.get(rb_code)
    if rb_code:
        return rb.meta
    raise ApiException(404, 'Reference Book not found')


@module.route('/v2/rb/<rb_code>/meta/', methods=['PUT'])
@api_method
def rb_put(rb_code):
    """
    Изменение метаданных справочника
    :param rb_code:
    :return:
    """
    j = flask.request.get_json()
    rb = RefBookRegistry.get(rb_code)
    rb.meta.update(j)
    rb.meta.reshape()
    return rb.meta


@module.route('/v2/rb/<rb_code>/data/', methods=['GET'])
@api_method
def rb_records_get(rb_code):
    """
    Получение всех данных из справочника
    :param rb_code:
    :return:
    """
    skip = flask.request.args.get('skip') or None
    limit = flask.request.args.get('limit') or 100
    rb = RefBookRegistry.get(rb_code)
    return rb.find({}, 'code', limit=limit, skip=skip)


@module.route('/v2/rb/<rb_code>/data/id/<rec_id>/', methods=['GET'])
@api_method
def rb_record_get_id(rb_code, rec_id):
    """
    Получение записи из справочника
    :param rb_code:
    :param rec_id:
    :return:
    """
    rb = RefBookRegistry.get(rb_code)
    record = rb.find_one({'_id': bson.ObjectId(rec_id)})
    return record


@module.route('/v2/rb/<rb_code>/data/id/<rec_id>/', methods=['PUT'])
@api_method
def rb_record_put_id(rb_code, rec_id):
    rb = RefBookRegistry.get(rb_code)
    record = rb.find_one({'_id': bson.ObjectId(rec_id)})
    record.update(flask.request.get_json())
    rb.save(record)
    return record


@module.route('/v2/rb/<rb_code>/data/code/<rec_code>/', methods=['GET'])
@api_method
def rb_record_get_code(rb_code, rec_code):
    """
    Получение записи из справочника
    :param rb_code:
    :param rec_code:
    :return:
    """
    rb = RefBookRegistry.get(rb_code)
    record = rb.find_one({'code': rec_code})
    return record


@module.route('/v2/rb/<rb_code>/data/code/<rec_code>/', methods=['PUT'])
@api_method
def rb_record_put_code(rb_code, rec_code):
    rb = RefBookRegistry.get(rb_code)
    record = rb.find_one({'code': rec_code})
    record.update(flask.request.get_json())
    rb.save(record)
    return record


@module.route('/v2/rb/<rb_code>/data/', methods=['POST'])
@api_method
def rb_record_post(rb_code):
    rb = RefBookRegistry.get(rb_code)
    record = rb.record_factory()
    record.update(flask.request.get_json())
    rb.save(record)
    return record

