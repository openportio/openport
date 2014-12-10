import threading
import sys
import urllib
import urllib2
from bottle import route, run, request, error, hook

from manager import dbhandler
from manager.globals import Globals
from services.logger_service import get_logger
from time import sleep
from manager.openportmanager import get_and_save_manager_port

logger = get_logger('server')


def app_communicate(share, path, data=None):
    url = 'http://127.0.0.1:%s/%s' % (share.app_management_port, path)
    logger.debug('sending get request ' + url)
    try:
        if data:
            data = urllib.urlencode(data)
            req = urllib2.Request(url, data)
        else:
            req = urllib2.Request(url)
        response = urllib2.urlopen(req, timeout=1).read()
        if response.strip() != 'ok':
            logger.error(response)
    except Exception, detail:
        Globals().app.notify_error(share)
        logger.error("An error has occurred while communicating with the app on %s: %s" % (url,detail))


def register_with_app(share):
    if share.app_management_port:
        app_communicate(share, 'register', {'port': Globals().manager_port})


@route('/newShare', method='POST')
def new_share(name='newShare'):
    form_data = request.forms
    logger.debug('/newShare ' + str(dict(form_data.iteritems())))

    id = int(form_data['id'])
    share = dbhandler.getInstance().get_share(id)
    if not share:
        return 'share not in db'

    Globals().account_id = share.account_id
    Globals().key_id = share.key_id

    Globals().app.add_share(share)
    return 'ok'


@route('/successShare', method='POST')
def success_share(name='success_share'):
    form_data = request.forms
    logger.debug('/success ' + str(dict(form_data.iteritems())))

    id = int(form_data['id'])
    share = dbhandler.getInstance().get_share(id)
    if not share:
        return 'share not in db'
    Globals().app.notify_success(share)

    return 'ok'


@route('/errorShare', method='POST')
def error_share(name='error_share'):
    form_data = request.forms
    logger.debug('/failure ' + str(dict(form_data.iteritems())))

    id = int(form_data['id'])
    share = dbhandler.getInstance().get_share(id)
    if not share:
        return 'share not in db'
    Globals().app.notify_error(share)

    return 'ok'


@route('/stopShare', method='POST')
def stop_share(name='stop_share'):
    form_data = request.forms
    logger.debug('/stop ' + str(dict(form_data.iteritems())))

    id = int(form_data['id'])
    share = dbhandler.getInstance().get_share(id)
    if not share:
        return 'share not in db'

    Globals().app.remove_share(share)
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
            Globals().app.exitApp('server_exit')
        t = threading.Thread(target=shutdown)
        t.setDaemon(True)
        t.start()
        return 'ok'


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
    get_and_save_manager_port()
    try:
        logger.info('Starting the manager on port %s' % Globals().manager_port)
        run(host='127.0.0.1', port=Globals().manager_port, server='cherrypy', debug=True, quiet=True)
    except KeyboardInterrupt:
        pass


def start_server_thread():
    t = threading.Thread(target=start_server)
    t.setDaemon(True)
    t.start()

if __name__ == '__main__':
    print sys.argv
    start_server()
