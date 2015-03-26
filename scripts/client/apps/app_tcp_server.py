import threading
import sys
import urllib
import urllib2
from urllib2 import URLError

from bottle import route, run, request, error, hook

from manager import dbhandler
from manager.globals import Globals
from services.logger_service import get_logger
from time import sleep
from services.osinteraction import getInstance
import os
logger = get_logger('server')

globals = Globals.Instance()

@route('/register', method='POST')
def new_share(name='register'):
    form_data = request.forms
    logger.debug('/register ' + str(dict(form_data.iteritems())))

    port = int(form_data['port'])
    Globals.Instance().tcp_listeners.add(port)
    return 'ok'

@route('/ping', method='GET')
def ping():
    return 'pong'


@route('/exit', method='POST', )
def exit_manager():
    logger.debug('/exit')
    if request.remote_addr == '127.0.0.1':
        force = request.forms.get('force', False)

        def shutdown():
            sleep(1)
            logger.debug('shutting down due to exit call. Force: %s' % force)
            if force:
                os._exit(5)
            import signal
            Globals.Instance().app.handleSigTERM(signal.SIGINT)
        t = threading.Thread(target=shutdown)
        t.setDaemon(True)
        t.start()
        return 'ok'


def inform_listeners(share, path):
    def inform():
        for port in Globals.Instance().tcp_listeners.copy():
            logger.debug('Informing %s to %s.' % (path, port))
            url = 'http://127.0.0.1:%s/%s' % (port, path)
            logger.debug('sending get request ' + url)
            try:
                data = urllib.urlencode({'id': share.id})
                logger.debug(data)
                req = urllib2.Request(url, data)
                response = urllib2.urlopen(req, timeout=1).read()
                if response.strip() != 'ok':
                    logger.error(response)
            except URLError:
                Globals.Instance().tcp_listeners.remove(port)
            except Exception, detail:
                logger.error("An error has occurred while informing the manager: %s" % detail)
    t = threading.Thread(target=inform)
    t.setDaemon(True)
    t.start()


def inform_start(share):
    inform_listeners(share, 'newShare')


def inform_success(share):
    inform_listeners(share, 'successShare')


def inform_failure(share, exception):
    inform_listeners(share, 'errorShare')


def inform_stop(share):
    inform_listeners(share, 'stopShare')


def send_exit(share, force=False):
    port = share.app_management_port
    logger.debug('Sending exit to %s.' % port)
    url = 'http://127.0.0.1:%s/exit' % (port,)
    logger.debug('sending get request ' + url)
    try:
        data = urllib.urlencode({'id': share.id, 'force': force})
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req, timeout=1).read()
        if response.strip() != 'ok':
            logger.error(response)
    except Exception, detail:
        logger.error("An error has occurred while killing the app: %s" % detail)


def send_ping(share):
    port = share.app_management_port
    logger.debug('Sending exit to %s.' % port)
    url = 'http://127.0.0.1:%s/ping' % (port,)
    logger.debug('sending get request ' + url)
    try:
        req = urllib2.Request(url)
        response = urllib2.urlopen(req, timeout=1).read()
        if response.strip() != 'pong':
            logger.error(response)
            return False
        return True
    except Exception, detail:
        logger.error("An error has occurred while pinging the app: %s" % detail)


@route('/error', method='GET')
def error_():
    raise Exception('The short error message.')


@error(500)
def custom500(httpError):
    logger.error(httpError.exception)
    return 'An error has occurred: %s' % httpError.exception

@hook('after_request')
def close_db_connections():
    # Double tap? Session should be already closed...
    dbhandler.getInstance().Session.remove()

def start_server():
    port = getInstance().get_open_port()

    session = Globals.Instance().app.session
    session.app_management_port = port

    try:
        session.start_observers.append(inform_start)
        session.success_observers.append(inform_success)
        session.error_observers.append(inform_failure)
        session.stop_observers.append(inform_stop)
        logger.info('Starting the app management on port %s' % port)
        run(host='127.0.0.1', port=port, server='cherrypy', debug=True, quiet=True)
    except KeyboardInterrupt:
        pass

def start_server_thread():
    t = threading.Thread(target=start_server)
    t.setDaemon(True)
    t.start()

if __name__ == '__main__':
    print sys.argv
    start_server()
