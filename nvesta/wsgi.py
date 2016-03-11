import os

import flask

from nvesta.systemwide import app
from nvesta.usagicompat import VestaUsagiClient


usagi = VestaUsagiClient(app, os.getenv('TSUKINO_USAGI_URL', 'http://127.0.0.1:5900'), 'vesta')
app.wsgi_app = usagi.app
usagi()


@app.route('/')
def hello_world():
    return flask.redirect(flask.url_for('admin.index'))


if __name__ == '__main__':
    app.run(port=5006)
