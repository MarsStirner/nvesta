# -*- coding: utf-8 -*-
from flask import Flask
from flask.ext.fanstatic import Fanstatic
from flask.ext.pymongo import PyMongo
from flask.ext.cache import Cache

__author__ = 'viruzzz-kun'

app = Flask(__name__)

mongo = PyMongo()

fanstatic = Fanstatic()

cache = Cache()
