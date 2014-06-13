import json
import sys
import threading
import time
import datetime
import urllib2
import traceback
import signal
from time import sleep

import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from manager import dbhandler
from manager.server import start_server_thread
from services import osinteraction
from manager.globals import Globals
from services.logger_service import get_logger, set_log_level
from common.share import Share
from common.session import Session
from services.utils import nonBlockRead

logger = get_logger('OpenPortManager')


class OpenPortManager(object):

    def __init__(self):
        self.share_processes = {}
        self.dbhandler = dbhandler.getInstance()
        self.os_interaction = osinteraction.getInstance()
        self.globals = Globals()
        self.start_account_checking()
        if self.os_interaction.is_compiled():
            sys.stdout = open(self.os_interaction.get_app_data_path('application.out.log'), 'a')
            sys.stderr = open(self.os_interaction.get_app_data_path('application.error.log'), 'a')

    def exitApp(self,event):
        for pid in self.share_processes:
            try:
                logger.info("trying to kill pid %s" % (pid,))
                p = self.os_interaction.kill_pid(pid)
                logger.info("kill pid %s successful: %s" % (pid, p))
            except Exception, e:
                tb = traceback.format_exc()
                logger.error(e)
                logger.error(tb)
        sys.exit()

    def restart_sharing(self):
        shares = self.dbhandler.get_shares()
        logger.debug('restarting shares - amount: %s' % len(list(shares)))
        for share in shares:
            if self.os_interaction.pid_is_running(share.pid):
                logger.debug('share still running: %s' % share.restart_command)
                self.onNewShare(share)
            else:
                try:
                    logger.debug('starting share: %s' % share.restart_command)
                    p = self.os_interaction.start_openport_process(share, manager_port=Globals().manager_port)
                    sleep(1)
                    if p.poll() is not None:
                        logger.debug('could not start openport process: StdOut:%s\nStdErr:%s' %
                                     (nonBlockRead(p.stdout), nonBlockRead(p.stderr)))
                    else:
                        logger.debug('started app %s' % share.restart_command)
                        sleep(1)
                        logger.debug('app output: stdout: %s stderr: %s' % (nonBlockRead(p.stdout), nonBlockRead(p.stderr)))

                    self.share_processes[p.pid] = p
                except Exception, e:
                    tb = traceback.format_exc()
                    logger.error('Error: <<<' + tb + ' >>>')

    def stop_sharing(self,share):
        logger.info("stopping %s" % share.id)
        self.os_interaction.kill_pid(share.pid)
        self.dbhandler.stop_share(share)

    def onNewShare(self, share):
        logger.info( "adding share %s" % share.id )
        logger.debug( share.restart_command)
        share.success_observers.append(self.onShareSuccess)
        share.error_observers.append(self.onShareError)
        share.stop_observers.append(self.stop_sharing)

        self.share_processes[share.pid] = None

    def onShareError(self, share):
        pass

    def onShareSuccess(self, share):
        pass

    def start_account_checking(self):

        def check_account_loop():
            while True:
                if self.globals.account_id == -1:
                    time.sleep(1)
                else:
                    try:
                        dict = self.check_account()
                        self.show_account_status(dict)
                    except Exception, detail:
                        logger.error("An error has occurred while communicating the the openport servers. %s" % detail)
                        pass

                    time.sleep(60)
        t = threading.Thread(target=check_account_loop)
        t.setDaemon(True)
        t.start()

    def check_account(self):
        url = 'http://%s/api/v1/account/%s/%s' % (self.globals.openport_address, self.globals.account_id, self.globals.key_id)
        logger.debug('checking account: %s' % url)
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req).read()
            logger.debug( response )
            dict = json.loads(response)
            if 'error' in dict:
                logger.error( dict['error'] )
            return dict
        except Exception, detail:
            logger.error( "An error has occurred while communicating the the openport servers. %s" % detail )
            raise detail
            #sys.exit(9)

    def show_account_status(self, dict):
        pass #catching a signal and showing info? #logging to /proc ?

    def startOpenportItProcess (self, path):
        share = Share()
        share.filePath = path
        app_dir = self.os_interaction.get_application_dir()
        if self.os_interaction.is_compiled():
            share.restart_command = [os.path.join(app_dir, 'openportit.exe'), path]
        else:
            share.restart_command = ['python', os.path.join(app_dir, 'apps/openportit.py'), path]

        p = self.os_interaction.start_openport_process(share, hide_message=False, no_clipboard=False,
                                                   manager_port=Globals().manager_port)

    def startOpenportProcess (self, port):
        session = Session()
        app_dir = self.os_interaction.get_application_dir()
        if self.os_interaction.is_compiled():
            session.restart_command = [os.path.join(app_dir, 'openport_app.exe'), '--local-port', '%s' % port]
        else:
            session.restart_command = ['python', os.path.join(app_dir,'apps/openport_app.py'), '--local-port', '%s' % port]
        logger.debug(session.restart_command)

        self.os_interaction.start_openport_process(session, hide_message=False, no_clipboard=False,
                                                   manager_port=Globals().manager_port)

    def print_shares(self):
        shares = self.dbhandler.get_shares()
        logger.debug('listing shares - amount: %s' % len(list(shares)))
        for share in shares:
            print self.get_share_line(share)

    def get_share_line(self, share):
               #"pid: %s - " % share.pid + \
        return "localport: %s - " % share.local_port + \
               "remote port: %s - " % share.server_port + \
               "running: %s" % self.os_interaction.pid_is_running(share.pid)

    def kill(self, local_port):
        shares = self.dbhandler.get_share_by_local_port(local_port)
        if len(shares) > 0:
            share = shares[0]
            if self.os_interaction.pid_is_running(share.pid):
                self.os_interaction.kill_pid(share.pid)
            self.dbhandler.stop_share(share)
        self.print_shares()


def utc_epoch_to_local_datetime(utc_epoch):
    return datetime.datetime(*time.localtime(utc_epoch)[0:6])

if __name__ == '__main__':
    logger.debug('server pid:%s' % os.getpid())

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dont-restart-shares', action='store_false', dest='restart_shares', help='Restart all active shares.')
    parser.add_argument('--verbose', action='store_true', help='Be verbose.')
    parser.add_argument('--database', '-d', action='store', help='Use the following database file.', default='')
    parser.add_argument('--manager-port', '-p', action='store', type=int,
                        help='The port the manager communicates on with it''s child processes.', default=8001) #TODO random port??
    parser.add_argument('--server', '-s', action='store', type=str, default='www.openport.be', help=argparse.SUPPRESS)
    parser.add_argument('--list', '-l', action='store_true', help="list shares and exit")
    parser.add_argument('--kill', '-k', action='store', type=int, help="list shares and exit", default=0)
    args = parser.parse_args()

    dbhandler.db_location = args.database

    if args.verbose:
        from logging import DEBUG
        set_log_level(DEBUG)
        logger.debug('You are seeing debug output.')

    manager = OpenPortManager()

    Globals().manager_port = args.manager_port
    Globals().openport_address = args.server

    if args.list:
        manager.print_shares()
        exit()

    if args.kill:
        manager.kill(args.kill)
        exit()

    start_server_thread(onNewShare=manager.onNewShare)

    sleep(1)

    if args.restart_shares:
        manager.restart_sharing()

    def handleSigTERM(signum, frame):
        logger.debug('got a signal %s, frame %s going down' % (signum, frame))
        manager.exitApp(None)
    signal.signal(signal.SIGTERM, handleSigTERM)
    signal.signal(signal.SIGINT, handleSigTERM)

    while True:
        sleep(1)


