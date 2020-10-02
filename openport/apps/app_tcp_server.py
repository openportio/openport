import sys
from time import sleep
import os
import threading
import requests

from bottle import Bottle, ServerAdapter, request, response, error, hook
from openport.services.logger_service import get_logger
from openport.services.utils import run_method_with_timeout


logger = get_logger('server')


class CherryPyServer(ServerAdapter):
    def run(self, handler):
        try:
            from cheroot.wsgi import Server as CherryPyWSGIServer
        except ImportError:
            from cherrypy.wsgiserver import CherryPyWSGIServer

        self.server = CherryPyWSGIServer((self.host, self.port), handler)
        try:
            self.server.start()
        finally:
            self.server.stop()

    def stop(self):
        if hasattr(self, 'server'):
            self.server.stop()


class AppTcpServer():
    
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

        @self.app.route('/register', method='POST')
        @self.enable_cors
        def new_share(name='register'):
            form_data = request.forms
            logger.debug('/register ' + str(dict(form_data.iteritems())))
        
            port = int(form_data['port'])
            self.openport_app_config.tcp_listeners.add(port)
            return 'ok'
        
        @self.app.route('/ping', method='GET')
        @self.enable_cors
        def ping():
            return 'pong'
        
        @self.app.route('/exit', method='POST', )
        @self.enable_cors
        def exit():
            logger.debug('/exit')
            if request.remote_addr == '127.0.0.1':
                force = request.forms.get('force', False)

                def shutdown():
                    sleep(1)
                    logger.debug('shutting down due to exit call. Force: %s' % force)
                    if force:
                        os._exit(5)
                    import signal
                    self.openport_app_config.app.handleSigTERM(signal.SIGINT)
                t = threading.Thread(target=shutdown)
                t.setDaemon(True)
                t.start()
                return 'ok'

        @self.app.route('/error', method='GET')
        @self.enable_cors
        def error_():
            raise Exception('The short error message.')

        @self.app.route('/info', method='GET')
        @self.enable_cors
        def info():
            return 'openport'
        
        @error(500)
        def custom500(httpError):
            logger.error(httpError.exception)
            return 'An error has occurred: %s' % httpError.exception
        
        @hook('after_request')
        def close_db_connections():
            # Double tap? Session should be already closed...
            if self.db_handler:
                self.db_handler.Session.remove()

    def inform_listeners(self, share, path):
        def inform():
            for port in self.openport_app_config.tcp_listeners.copy():
                logger.debug('Informing %s to %s.' % (path, port))
                url = 'http://127.0.0.1:%s/%s' % (port, path)
                logger.debug('sending get request ' + url)
                try:
                    data = {'id': share.id}
                    logger.debug(data)
                    r = requests.post(url, data=data, timeout=1)
                    if r.text.strip() != 'ok':
                        logger.error(response)
                except requests.ConnectionError:
                    self.openport_app_config.tcp_listeners.remove(port)
                except Exception as detail:
                    logger.error("An error has occurred while informing the manager: %s" % detail)
        t = threading.Thread(target=inform)
        t.setDaemon(True)
        t.start()

    def inform_start(self, share):
        self.inform_listeners(share, 'newShare')

    def inform_success(self, share):
        self.inform_listeners(share, 'successShare')

    def inform_failure(self, share, exception):
        self.inform_listeners(share, 'errorShare')

    def inform_stop(self, share):
        self.inform_listeners(share, 'stopShare')

    def run(self):
        self.running = True
        logger.debug('starting openport app server on port %s' % self.server.port)
        self.app.run(server=self.server, debug=True, quiet=True)
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


def send_exit(share, force=False):
    port = share.app_management_port
    logger.debug('Sending exit to %s.' % port)
    url = 'http://127.0.0.1:%s/exit' % (port,)
    logger.debug('sending get request ' + url)
    try:
        data = {'id': share.id, 'force': force}
        r = requests.post(url, data=data, timeout=1)
        if r.text.strip() != 'ok':
            logger.error(response)
    except Exception as detail:
        logger.error("An error has occurred while killing the app: %s" % detail)


def send_ping(share, print_error=True):
    port = share.app_management_port
    logger.debug('Sending ping to %s.' % port)
    url = 'http://127.0.0.1:%s/ping' % (port,)
    logger.debug('sending get request ' + url)
    try:
        r = run_method_with_timeout(requests.get, 5, args=[url])
        if r.text.strip() != 'pong':
            logger.error(response)
            return False
        return True
    except Exception as detail:
        log_function = logger.error if print_error else logger.debug
        log_function("An error has occurred while pinging the app: %s" % detail)
        return False


def is_running(share, print_error=False):
    port = share.app_management_port
    logger.debug('Sending info to %s.' % port)
    url = 'http://127.0.0.1:%s/info' % (port,)
    logger.debug('sending get request ' + url)
    try:
        r = requests.get(url, timeout=1)
        if r.text.splitlines()[0].strip() != 'openport':
            logger.error(response)
            return False
        return True
    except Exception as detail:
        logger_function = logger.error if print_error else logger.debug
        logger_function("An error has occurred while getting info from the app: %s" % detail)
        return False


if __name__ == '__main__':
    print(sys.argv)

    from common.config import OpenportAppConfig
    server = AppTcpServer('127.0.0.1', 6005, OpenportAppConfig(), None)
    server.run()
