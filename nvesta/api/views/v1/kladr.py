# -*- coding: utf-8 -*-
import flask

from hitsl_utils.api import crossdomain
from nvesta.api.app import module
from nvesta.api.views.v1.apiutils import v1_jsonify, v1_api_method
from nvesta.library.shape import RefBookRegistry
from nvesta.library.utils import prepare_find_params
from nvesta.systemwide import cache

CITY_CODE = 'KLD172'
STREET_CODE = 'STR172'


@module.route('/kladr/city/search/<value>/', methods=['GET'])
@module.route('/kladr/city/search/<value>/<int:limit>/', methods=['GET'])
@crossdomain('*', methods=['GET'])
@cache.memoize(86400)
@v1_api_method
def search_city(value, limit=None):
    rb = RefBookRegistry.get(CITY_CODE)
    find = {
        'is_actual': '1',
        '$or': [
            {'name': prepare_find_params(value)},
            {'identcode': value}
        ]
    }
    cities = rb.find(find, 'level', limit)
    result = _set_cities_parents(cities)
    return result


@module.route('/kladr/psg/search/<value>/', methods=['GET'])
@module.route('/kladr/psg/search/<value>/<int:limit>/', methods=['GET'])
@crossdomain('*', methods=['GET'])
@cache.memoize(86400)
@v1_api_method
def search_city_country(value, limit=None):
    rb = RefBookRegistry.get(CITY_CODE)
    find = {
        'is_actual': '1',
        '$or': [
            {'name': prepare_find_params(value)},
            {'identcode': value}
        ]
    }
    cities = rb.find(find, 'level', limit)
    result = _set_cities_parents(cities)
    return result


@module.route('/kladr/street/search/<city_code>/', methods=['GET'])
@module.route('/kladr/street/search/<city_code>/<value>/', methods=['GET'])
@module.route('/kladr/street/search/<city_code>/<value>/<int:limit>/', methods=['GET'])
@crossdomain('*', methods=['GET'])
@cache.memoize(86400)
@v1_api_method
def search_street(city_code, value=None, limit=None):
    rb = RefBookRegistry.get(STREET_CODE)
    find = {
        'identparent': city_code,
        'is_actual': '1'
    }
    if value:
        prepared = prepare_find_params(value)
        find.update({
            '$or': [
                {'name': prepared},
                {'fulltype': prepared},
                {'shorttype': prepared},
                {'identcode': value}
            ]
        })
    result = rb.find(find, 'name', limit)
    return list(result)


@module.route('/kladr/city/<code>/', methods=['GET'])
@crossdomain('*', methods=['GET'])
@cache.memoize(86400)
@v1_api_method
def get_city(code):
    rb = RefBookRegistry.get(CITY_CODE)
    find = {'identcode': code}
    cities = rb.find(find)
    result = _set_cities_parents(cities)
    return result


@module.route('/kladr/street/<code>/', methods=['GET'])
@crossdomain('*', methods=['GET'])
@cache.memoize(86400)
@v1_api_method
def get_street(code):
    rb = RefBookRegistry.get(STREET_CODE)
    find = {'identcode': code}
    result = rb.find(find)
    return list(result)


def _set_cities_parents(cities):
    rb = RefBookRegistry.get(CITY_CODE)
    result = []
    for city in cities:
        city['parents'] = []
        identparent = city['identparent']
        parent = city.get('parent')

        if identparent or parent:
            level = int(city['level'])
            for i in xrange(level - 1, 0, -1):
                if parent:
                    parent_city = rb.find_one({'_id': parent})
                elif identparent:
                    parent_city = rb.find_one({'identcode': identparent})
                else:
                    break
                city['parents'].append(parent_city)
                parent = parent_city['parent']
                identparent = parent_city['identparent']
        result.append(city)
    return result