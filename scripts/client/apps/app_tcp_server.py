import threading
import sys
import urllib
import urllib2

from bottle import route, run, request, error, hook

from manager import dbhandler
from manager.globals import Globals
from services.logger_service import get_logger
from time import sleep
from services.osinteraction import getInstance
logger = get_logger('server')

globals = Globals()
listeners = []

@route('/register', method='POST')
def new_share(name='register'):
    form_data = request.forms
    logger.debug('/register ' + str(dict(form_data.iteritems())))

    port = int(form_data['port'])
    listeners.append(port)
    return 'ok'

@route('/ping', method='GET')
def ping():
    return 'pong'


@route('/exit', method='GET', )
def exit_manager():
    logger.debug('/exit')
    if request.remote_addr == '127.0.0.1':
        def shutdown():
            sleep(1)
            logger.debug('shutting down due to exit call')
            Globals().app.session.notify_stop()
            import signal
            Globals().app.handleSigTERM(signal.SIGINT)
        t = threading.Thread(target=shutdown)
        t.setDaemon(True)
        t.start()
        return 'ok'


def inform_listeners(share, path):
    for port in listeners:
        logger.debug('Informing success to %s.' % port)
        url = 'http://127.0.0.1:%s/%s' % (port, path)
        logger.debug('sending get request ' + url)
        try:
            data = urllib.urlencode({'id': share.id})
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req, timeout=1).read()
            if response.strip() != 'ok':
                logger.error(response)
        except Exception, detail:
            logger.error("An error has occurred while informing the manager: %s" % detail)


def inform_success(share):
    inform_listeners(share, 'successShare')


def inform_failure(share):
    inform_listeners(share, 'errorShare')

def inform_stop(share):
    inform_listeners(share, 'stopShare')

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

    session = Globals().app.session
    session.app_port = port

    try:
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
