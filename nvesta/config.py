# -*- coding: utf-8 -*-

__author__ = 'viruzzz-kun'


DEBUG = True

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5004

WTF_CSRF_ENABLED = True
SECRET_KEY = '\xd0\x93l\x97{\xabU\x0c\x14\xb8k\xad\x99\xcc]Jut|\x02\xa7\x80\\1D\x91\xc8\xfc\x90\xaa\xd2c'

MONGO_HOST = '10.1.2.11'
MONGO_PORT = 27017
MONGO_USERNAME = ''
MONGO_PASSWORD = ''
MONGO_DBNAME = 'nvesta'

SIMPLELOGS_URL = 'http://127.0.0.1:8080'
NSI_SOAP = 'http://nsi.rosminzdrav.ru/wsdl/SOAP-server.v2.php?wsdl'
NSI_TOKEN = ''

CACHE_TYPE = 'filesystem'
CACHE_DIR = '/tmp/cache/nvesta'
