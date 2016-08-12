# -*- coding: utf-8 -*-
import flask

from hitsl_utils.api import api_method
from nvesta.api.app import module
from nvesta.library.rb.classes import DiffVersion, EdgeVersion
from nvesta.library.rb.registry import RefBookRegistry

__author__ = 'viruzzz-kun'


@module.route('/v2/rb/<rb_code>/diff/', methods=['GET'])
@api_method
def rb_diff(rb_code):
    rb = RefBookRegistry.get(rb_code)
    return [
        record.as_json(True, True)
        for record in rb.find({}, version=DiffVersion)
    ]


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
    edge = bool(flask.request.args.get('edge', False))
    with_meta = bool(flask.request.args.get('with-meta', False))
    version = edge and EdgeVersion or flask.request.args.get('version') or None
    rb = RefBookRegistry.get(rb_code)
    return [
        record.as_json(edge, with_meta)
        for record in rb.find({}, 'code', limit=limit, skip=skip, version=version)
    ]


@module.route('/v2/rb/<rb_code>/data/<field>/<rec_id>/', methods=['GET'])
@api_method
def rb_record_get_id(rb_code, field, rec_id):
    """
    Получение записи из справочника
    :param rb_code:
    :param rec_id:
    :return:
    """
    rb = RefBookRegistry.get(rb_code)
    edge = bool(flask.request.args.get('edge', False))
    with_meta = bool(flask.request.args.get('with-meta', False))
    version = edge and EdgeVersion or flask.request.args.get('version') or None
    record = rb.find_one(field, rec_id, version=version)
    return record.as_json(edge, with_meta)


@module.route('/v2/rb/<rb_code>/data/<field>/<rec_id>/', methods=['PUT'])
@api_method
def rb_record_put_id(rb_code, field, rec_id):
    rb = RefBookRegistry.get(rb_code)
    record = rb.find_one(field, rec_id, version=EdgeVersion)
    record.update(flask.request.get_json())
    record.save()
    return record.as_json(True, True)


@module.route('/v2/rb/<rb_code>/data/<field>/<rec_id>/', methods=['DELETE'])
@api_method
def rb_record_delete(rb_code, field, rec_id):
    rb = RefBookRegistry.get(rb_code)
    record = rb.find_one(field, rec_id, version=EdgeVersion)
    record.delete()
    record.save()
    return record.as_json(True, True)


@module.route('/v2/rb/<rb_code>/data/', methods=['POST'])
@api_method
def rb_record_post(rb_code):
    rb = RefBookRegistry.get(rb_code)
    record = rb.record_factory()
    record.update(flask.request.get_json())
    record.save()
    return record.as_json(True, True)
