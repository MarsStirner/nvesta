# -*- coding: utf-8 -*-
from nvesta.admin.app import module as admin_module
from nvesta.api.app import module as api_module
from nvesta.ext.app import module as ext_module
from nvesta.ext.library.ext_systems import ExtSystemProperties
from nvesta.library.rb import registry
from nvesta.systemwide import app, mongo, fanstatic
from tsukino_usagi.client import TsukinoUsagiClient

__author__ = 'viruzzz-kun'


class VestaUsagiClient(TsukinoUsagiClient):
    def on_configuration(self, configuration):
        app.config.update(configuration)

        mongo.init_app(app)
        fanstatic.init_app(app)

        with app.app_context():
            registry.RefBookRegistry.bootstrap(mongo.db)
            ExtSystemProperties.bootstrap(mongo.db)

        app.register_blueprint(admin_module, url_prefix='/admin')
        app.register_blueprint(api_module,   url_prefix='/api')
        app.register_blueprint(ext_module,   url_prefix='/ext')

        @app.after_request
        def app_after_request(response):
            """
            После каждого запроса надо инвалидировать реестр справочников, ибо неизвестно, что произошло с ними в
            других процессах
            """
            from nvesta.library.rb.registry import RefBookRegistry
            RefBookRegistry.invalidate()
            return response




