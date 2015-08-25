import sys
from time import sleep
import threading

from bottle import Bottle, ServerAdapter, request, response, run, error, hook
import requests
from services.logger_service import get_logger
from common.config import OpenportAppConfig

logger = get_logger('server')


class CherryPyServer(ServerAdapter):
    def run(self, handler):
        from cherrypy import wsgiserver

        self.server = wsgiserver.CherryPyWSGIServer((self.host, self.port), handler)
        try:
            self.server.start()
        finally:
            self.server.stop()

    def stop(self):
        if hasattr(self, 'server'):
            self.server.stop()


class GUITcpServer():

    # CORS (cross-origin resource sharing) decorator
    def enable_cors(self, fn):
        def _enable_cors(*args, **kwargs):
            # set CORS headers
            response.headers['Access-Control-Allow-Origin'] = '127.0.0.1'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
            response.headers[
                'Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

            if request.method != 'OPTIONS':
                # actual request; reply with the actual response
                return fn(*args, **kwargs)
            pass

        return _enable_cors

    def __init__(self, host, port, openport_app_config, db_handler):
        self.app = Bottle()
        self.server = CherryPyServer(host=host, port=port)
        self.running = False
        self.openport_app_config = openport_app_config
        self.db_handler = db_handler

        @self.app.route('/newShare', method='POST')
        @self.enable_cors
        def new_share(name='newShare'):
            form_data = request.forms
            logger.debug('/newShare ' + str(dict(form_data.iteritems())))

            id = int(form_data['id'])
            share = self.db_handler.get_share(id)
            if not share:
                logger.debug('share not in DB')
                return 'share not in db'

            self.openport_app_config.account_id = share.account_id
            self.openport_app_config.key_id = share.key_id

            self.openport_app_config.app.add_share_after(share)
            return 'ok'


        @self.app.route('/successShare', method='POST')
        @self.enable_cors
        def success_share(name='success_share'):
            form_data = request.forms
            logger.debug('/success ' + str(dict(form_data.iteritems())))

            id = int(form_data['id'])
            share = self.db_handler.get_share(id)
            if not share:
                return 'share not in db'
            self.openport_app_config.app.notify_success(share)

            return 'ok'


        @self.app.route('/errorShare', method='POST')
        @self.enable_cors
        def error_share(name='error_share'):
            form_data = request.forms
            logger.debug('/failure ' + str(dict(form_data.iteritems())))

            id = int(form_data['id'])
            share = self.db_handler.get_share(id)
            if not share:
                return 'share not in db'
            self.openport_app_config.app.notify_error(share)

            return 'ok'


        @self.app.route('/stopShare', method='POST')
        @self.enable_cors
        def stop_share(name='stop_share'):
            form_data = request.forms
            logger.debug('/stop ' + str(dict(form_data.iteritems())))

            id = int(form_data['id'])
            share = self.db_handler.get_share(id)
            if not share:
                return 'share not in db'

            self.openport_app_config.app.remove_share(share)
            return 'ok'


        @self.app.route('/ping', method='GET')
        @self.enable_cors
        def ping():
            return 'pong'


        @self.app.route('/exit', method='GET', )
        @self.enable_cors
        def exit_manager():
            logger.debug('/exit')
            if request.remote_addr == '127.0.0.1':
                def shutdown():
                    sleep(1)
                    logger.debug('shutting down due to exit call')
                    self.openport_app_config.app.exitApp('server_exit')
                t = threading.Thread(target=shutdown)
                t.setDaemon(True)
                t.start()
                return 'ok'


        @self.app.route('/error', method='GET')
        @self.enable_cors
        def error_():
            raise Exception('The short error message.')


        @self.app.error(500)
        def custom500(httpError):
            logger.error(httpError.exception)
            return 'An error has occurred: %s' % httpError.exception


        @self.app.hook('after_request')
        def close_db_connections():
            # Double tap? Session should be already closed...
            self.db_handler.Session.remove()


    def app_communicate(self, share, path, data=None):
        url = 'http://127.0.0.1:%s/%s' % (share.app_management_port, path)
        logger.debug('sending get request ' + url)
        try:
            r = requests.post(url, data=data, timeout=1)
            if r.text.strip() != 'ok':
                logger.error(r.text)
        except Exception, detail:
            self.openport_app_config.app.notify_app_down(share)
            logger.error("An error has occurred while communicating with the app on %s: %s" % (url, detail))

    def register_with_app(self, share):
        if share.app_management_port:
            self.app_communicate(share, 'register', {'port': self.openport_app_config.manager_port})

    def run(self):
        self.running = True
        logger.debug('starting openport gui server on port %s' % self.server.port)
        self.app.run(server=self.server, debug=True, quiet=False)
        self.running = False

    def run_threaded(self):
        t = threading.Thread(target=self.run)
        t.setDaemon(True)
        t.start()

    def stop(self):
        self.server.stop()

    def get_port(self):
        return self.server.port

    def set_port(self, port):
        self.server.port = port



if __name__ == '__main__':
    print sys.argv

    server = GUITcpServer('127.0.0.1', 6049, OpenportAppConfig())
    server.start_server()
