# -*- coding: utf-8 -*-
import functools
import traceback

import flask

from hitsl_utils.api import ApiException

__author__ = 'viruzzz-kun'


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
                    'message': u'Внутренняя ошибка сервера',
                }
            }), 500, {'Content-Type': 'application/json; charset=utf8'}
        else:
            return flask.jsonify(result), 200, {'Content-Type': 'application/json; charset=utf8'}
    return wrapper