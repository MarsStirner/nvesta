import flask

from nvesta.library import shape
from nvesta.systemwide import app, mongo, fanstatic
from nvesta.admin.app import module as admin_module
from nvesta.api.app import module as api_module

import config

app.config.from_object(config)

mongo.init_app(app)
fanstatic.init_app(app)

with app.app_context():
    shape.RefBookRegistry.bootstrap()

app.register_blueprint(admin_module, url_prefix='/admin')
app.register_blueprint(api_module,   url_prefix='/api')


@app.route('/')
def hello_world():
    return flask.redirect(flask.url_for('admin.index'))


if __name__ == '__main__':
    app.run(port=5006)
