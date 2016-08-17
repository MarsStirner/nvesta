# -*- coding: utf-8 -*-
import flask

from hitsl_utils.api import api_method, ApiException
from nvesta.api.app import module
from nvesta.library.rb.registry import RefBookRegistry
from nvesta.library.utils import bail_out

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
    rb = RefBookRegistry.create(j)
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


@module.route('/v2/rb/<rb_code>/fix/', methods=['POST'])
@api_method
def rb_version_fix(rb_code):
    version = flask.request.args.get('version') or bail_out(ApiException(400, 'Need "version" argument'))
    rb = RefBookRegistry.get(rb_code)
    rb.fixate(version)
    return rb.meta


