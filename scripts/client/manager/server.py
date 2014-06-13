import cgi
import urlparse
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import signal
import threading
import sys

from bottle import route, run, request


from manager import dbhandler
import os
from common.session import Session
from manager.globals import Globals
from common.share import Share
from services.logger_service import get_logger
from time import sleep
logger = get_logger('server')

onNewShare = None
globals = Globals()
shares = {}

@route('/newShare', method='POST')
def new_share(name='newShare'):

    form_data = request.forms

    if form_data['local_port'] in shares:
        #update existing share
        share = shares[form_data['local_port']]
        share.from_dict(form_data)
    else:
        if form_data['type'] == 'Share':
            share = Share()
        else:
            share = Session()
        share.from_dict(form_data)

        globals.account_id = share.account_id
        globals.key_id = share.key_id
#                    logger.debug( 'path: <%s>' % share.filePath )

        save_request(share)
        if onNewShare:
            onNewShare(share)
        global shares
        shares[share.local_port] = share
        logger.debug('added new share')
        logger.debug(shares)
    return 'ok'


@route('/successShare', method='GET')
def success_share_get():
    return 'only post allowed'

@route('/successShare', method='POST')
def success_share():
    logger.debug('success')
    form_data = request.forms

    if not form_data['local_port'] in shares:
        logger.error('unknown key: %s in shares %s' % (form_data['local_port'], shares))
        return 'unknown'
    else:
        shares[form_data['local_port']].notify_success()
        return 'ok'


@route('/errorShare', method='POST')
def error_share():
    logger.debug('error')
    form_data = request.forms
    if not form_data['local_port'] in shares:
        logger.error('unknown key: %s in shares %s' % (form_data['local_port'], shares))
        return 'unknown'
    else:
        shares[form_data['local_port']].notify_error()
        return 'ok'


@route('/stopShare', method='POST')
def stop_share():
    logger.debug('stopShare')
    form_data = request.forms

    if not form_data['local_port'] in shares:
        logger.error('unknown key: %s in shares %s' % (form_data['local_port'], shares))
        return 'unknown'
    else:
        shares[form_data['local_port']].notify_stop()
        #self.write_response('ok') # no need to answer


@route('/ping', method='GET')
def ping():
    return 'pong'


@route('/exit', method='GET', )
def exit_manager():
    if request.remote_addr == '127.0.0.1':
        def shutdown():
            sleep(1)
            logger.debug('shutting down due to exit call')
            os.kill(os.getpid(), signal.SIGINT)
        t = threading.Thread(target=shutdown)
        t.setDaemon(True)
        t.start()
        return 'ok'


@route('/active_count', method='GET')
def active_count():
    return str(len(shares))


def start_server(onNewShareFunc=None):
    global onNewShare
    onNewShare = onNewShareFunc
    try:
        run(host='localhost', port=globals.manager_port)
    except KeyboardInterrupt:
        pass


def save_request(share):
    db_handler = dbhandler.getInstance()
    return db_handler.add_share(share)


def start_server_thread(onNewShare=None):
    t = threading.Thread(target=start_server, args=[onNewShare])
    t.setDaemon(True)
    t.start()

if __name__ == '__main__':
    print sys.argv
    start_server()
