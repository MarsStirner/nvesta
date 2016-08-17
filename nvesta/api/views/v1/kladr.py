# -*- coding: utf-8 -*-

from hitsl_utils.api import crossdomain
from hitsl_utils.safe import safe_dict, safe_int
from nvesta.api.app import module
from nvesta.api.views.v1.apiutils import v1_api_method
from nvesta.library.rb.registry import RefBookRegistry
from nvesta.library.utils import prepare_find_params

CITY_CODE = 'KLD172'
STREET_CODE = 'STR172'


@module.route('/kladr/city/search/<value>/', methods=['GET'])
@module.route('/kladr/city/search/<value>/<int:limit>/', methods=['GET'])
@crossdomain('*', methods=['GET'])
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
@v1_api_method
def get_city(code):
    rb = RefBookRegistry.get(CITY_CODE)
    find = {'identcode': code}
    cities = rb.find(find)
    result = _set_cities_parents(cities)
    return result


@module.route('/kladr/street/<code>/', methods=['GET'])
@crossdomain('*', methods=['GET'])
@v1_api_method
def get_street(code):
    rb = RefBookRegistry.get(STREET_CODE)
    find = {'identcode': code}
    result = rb.find(find)
    return list(result)


def _safe_city(city):
    return dict(
        safe_dict(city),
        level=safe_int(city['level']),
        status=safe_int(city['status'])
    )


def _get_parents(city):
    rb = RefBookRegistry.get(CITY_CODE)
    result = []

    def _get_parent(c, f=False):
        if c['identparent']:
            _get_parent(rb.find_one({'identcode': c['identparent']}))
        if not f:
            result.append(_safe_city(c))

    _get_parent(city, True)
    return result


def _set_cities_parents(cities):
    return [
        dict(
            _safe_city(city),
            parents=_get_parents(city),
        )
        for city in cities
    ]
