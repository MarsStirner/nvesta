# -*- coding: utf-8 -*-
import functools
import json
import traceback

import datetime

import bson
import flask

from hitsl_utils.api import ApiException

__author__ = 'viruzzz-kun'


class MongoJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, bson.ObjectId):
            return unicode(obj)
        elif hasattr(obj, '__json__'):
            return obj.__json__()
        return json.JSONEncoder.default(self, obj)


def v1_jsonify(obj):
    """ jsonify with support for MongoDB ObjectId"""
    return flask.Response(
        json.dumps(obj, cls=MongoJsonEncoder, ensure_ascii=False, indent=0),
        mimetype='application/json',
        content_type='application/json; charset=utf-8'
    )


def core_api_method(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except ApiException, e:
            traceback.print_exc()
            return flask.jsonify({
                'meta': {
                    'status': 'error',
                    'message': e.message
                }
            }), e.code, {'Content-Type': 'application/json; charset=utf8'}
        except Exception, e:
            traceback.print_exc()
            return flask.jsonify({
                'meta': {
                    'status': 'error',
                    'message': u'Внутренняя ошибка сервера. %s' % e.message,
                }
            }), 500, {'Content-Type': 'application/json; charset=utf8'}
        else:
            return flask.jsonify(result), 200, {'Content-Type': 'application/json; charset=utf8'}
    return wrapper


def v1_api_method(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except ApiException, e:
            traceback.print_exc()
            return v1_jsonify({
                'meta': {
                    'status': 'exception',
                    'code': e.code,
                    'message': e.message,
                },
                'data': None,
            })
        except Exception, e:
            traceback.print_exc()
            return v1_jsonify({
                'meta': {
                    'status': 'exceprion',
                    'code': 500,
                    'message': e.message,
                },
                'data': None,
            })
        else:
            return v1_jsonify({
                'meta': {
                    'code': 200,
                    'message': 'OK',
                },
                'data': result
            })
    return wrapper
