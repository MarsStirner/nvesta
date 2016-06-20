# -*- coding: utf-8 -*-
from tsukino_usagi.client import TsukinoUsagiClient
from nvesta.systemwide import app, mongo, fanstatic, cache
from nvesta.library import shape
from nvesta.admin.app import module as admin_module
from nvesta.api.app import module as api_module


__author__ = 'viruzzz-kun'


class VestaUsagiClient(TsukinoUsagiClient):
    def on_configuration(self, configuration):
        app.config.update(configuration)

        mongo.init_app(app)
        fanstatic.init_app(app)
        cache.init_app(app)

        with app.app_context():
            shape.RefBookRegistry.bootstrap(mongo.db)

        app.register_blueprint(admin_module, url_prefix='/admin')
        app.register_blueprint(api_module,   url_prefix='/api')





