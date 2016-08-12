# -*- coding: utf-8 -*-
from flask import Flask
from flask_beaker import BeakerSession
from flask_cache import Cache
from flask_fanstatic import Fanstatic
from flask_pymongo import PyMongo

__author__ = 'viruzzz-kun'

app = Flask(__name__)
mongo = PyMongo()
fanstatic = Fanstatic()
cache = Cache()
beaker = BeakerSession()