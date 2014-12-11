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
import argparse
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from manager import dbhandler
#from manager.server import start_server_thread
from services import osinteraction
from manager.globals import Globals
from services.logger_service import get_logger, set_log_level
from common.share import Share
from manager.globals import DEFAULT_SERVER
from services.osinteraction import is_windows
from services.config_service import get_and_save_manager_port

logger = get_logger('OpenPortManager')

manager_instance = None


class OpenPortManager(object):

    def __init__(self):
        self.share_processes = {}
        self.dbhandler = dbhandler.getInstance()
        self.os_interaction = osinteraction.getInstance()
        self.globals = Globals()

        if self.os_interaction.is_compiled():
            from common.tee import TeeStdErr, TeeStdOut
            TeeStdOut(self.os_interaction.get_app_data_path('openportmanager.out.log'), 'a')
            TeeStdErr(self.os_interaction.get_app_data_path('openportmanager.error.log'), 'a')

        self.start_account_checking()

    def exitApp(self, event):
        logger.debug('exiting, killing all sub processes: %s' % len(self.share_processes))
        for pid in self.share_processes:
            try:
                logger.info("trying to kill pid %s" % (pid,))
                p = self.os_interaction.kill_pid(pid)
                logger.info("kill pid %s successful: %s" % (pid, p))
                if self.share_processes[pid] is not None:
                    logger.debug('child process output: ' + str(self.os_interaction.non_block_read(self.share_processes[pid])))
            except Exception, e:
                tb = traceback.format_exc()
                logger.error(e)
                logger.error(tb)
        os._exit(3)
        #sys.exit()

    # def restart_sharing(self):
    #     shares = self.dbhandler.get_shares_to_restart()
    #     logger.debug('restarting shares - amount: %s' % len(list(shares)))
    #     shutdown = True
    #     for share in shares:
    #         if self.os_interaction.pid_is_openport_process(share.pid):
    #             logger.debug('share still running. Pid: %s command: %s' % (share.pid, share.restart_command))
    #             self.onNewShare(share)
    #         else:
    #             shutdown = False
    #             try:
    #                 logger.debug('restarting share: %s' % share.restart_command)
    #                 self.set_manager_port(share)
    #
    #                 p = self.os_interaction.start_openport_process(share)
    #                 self.os_interaction.print_output_continuously_threaded(p, 'share port: %s - ' % share.local_port)
    #                 sleep(1)
    #                 if p.poll() is not None:
    #                     logger.debug('could not start openport process: StdOut:%s\nStdErr:%s' %
    #                                  self.os_interaction.non_block_read(p))
    #                 else:
    #                     logger.debug('started app with pid %s : %s' % (p.pid, share.restart_command))
    #                     sleep(1)
    #
    #                 self.share_processes[p.pid] = p
    #             except Exception, e:
    #                 tb = traceback.format_exc()
    #                 logger.error('Error: <<<' + tb + ' >>>')
    #     users_file = '/etc/openport/users.conf'
    #     if not is_windows() and self.os_interaction.user_is_root() and os.path.exists(users_file):
    #         with open(users_file, 'r') as f:
    #             lines = f.readlines()
    #             for line in lines:
    #                 if not line.strip() or line.strip()[0] == '#':
    #                     continue
    #                 username = line.strip().split()[0]
    #
    #                 command = ['sudo', '-u', username, '-H', 'openport', 'manager', '--restart-shares']
    #                 logger.debug('restart command: %s' % command)
    #                 self.os_interaction.spawn_daemon(command)
    #
    #     if shutdown:
    #         logger.info('Started no shares, shutting down.')
    #         sys.exit(0)

    def stop_sharing(self, share):
        logger.info("stopping %s" % share.id)
        self.os_interaction.kill_pid(share.pid, signal.SIGTERM)
        self.dbhandler.stop_share(share)

    def onNewShare(self, share):
        logger.info("adding share %s" % share.local_port)
        logger.debug(share.restart_command)
        share.success_observers.append(self.onShareSuccess)
        share.error_observers.append(self.onShareError)
        share.stop_observers.append(self.stop_sharing)

        self.share_processes[share.pid] = None

    def onShareError(self, share, exception):
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
                        logger.error("An error has occurred while communicating with the openport servers. %s" % detail)
                        pass

                    time.sleep(60)
        t = threading.Thread(target=check_account_loop)
        t.setDaemon(True)
        t.start()

    def check_account(self):
        url = 'https://%s/api/v1/account/%s/%s' % (self.globals.openport_address, self.globals.account_id, self.globals.key_id)
        logger.debug('checking account: %s' % url)
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req).read()
            logger.debug(response)
            response_dict = json.loads(response)
            if 'error' in response_dict:
                logger.error(response_dict['error'])
            return response_dict
        except Exception, detail:
            logger.error("An error has occurred while checking the account on the openport "
                         "servers. %s %s" % (url, detail))
            raise detail
            #sys.exit(9)

    def show_account_status(self, dict):
        pass #catching a signal and showing info? #logging to /proc ?

    def startOpenportItProcess (self, path):
        share = Share()
        share.filePath = path
        raise Exception('todo')
        p = self.os_interaction.start_openport_process(share, hide_message=False, no_clipboard=False,
                                                   manager_port=Globals().manager_port)
        self.share_processes[p.pid] = p

    # def print_shares(self):
    #     shares = self.dbhandler.get_shares()
    #     logger.debug('listing shares - amount: %s' % len(list(shares)))
    #     for share in shares:
    #         print self.get_share_line(share)
    #
    # def get_share_line(self, share):
    #            #"pid: %s - " % share.pid + \
    #     share_line = "localport: %s - " % share.local_port + \
    #                  "remote port: %s - " % share.server_port + \
    #                  "running: %s - " % self.os_interaction.pid_is_openport_process(share.pid) + \
    #                  "restart on reboot: %s" % bool(share.restart_command)
    #     if Globals().verbose:
    #         share_line += ' - pid: %s' % share.pid + \
    #                       ' - id: %s' % share.id
    #     return share_line

    # def kill(self, local_port):
    #     shares = self.dbhandler.get_share_by_local_port(local_port)
    #     if len(shares) > 0:
    #         share = shares[0]
    #         self.kill_share(share)
    #     self.print_shares()
    #
    # def kill_share(self, share):
    #     if self.os_interaction.pid_is_openport_process(share.pid):
    #         logger.debug('pid is running, will kill it: %s' % share.pid)
    #         self.os_interaction.kill_pid(share.pid)
    #         if share.pid in self.share_processes:
    #             logger.debug('pid found in share_processes')
    #             if self.share_processes[share.pid] is not None:
    #                 logger.debug('output from child process: ' + str(
    #                     self.os_interaction.non_block_read(self.share_processes[share.pid])))
    #     self.dbhandler.stop_share(share)
    #
    # def kill_all(self):
    #     shares = self.dbhandler.get_shares()
    #     for share in shares:
    #         self.kill_share(share)

def get_manager_instance():
    global manager_instance
    if manager_instance is None:
        manager_instance = OpenPortManager()
    return manager_instance


def utc_epoch_to_local_datetime(utc_epoch):
    return datetime.datetime(*time.localtime(utc_epoch)[0:6])


def start_manager():
    logger.debug('server pid:%s' % os.getpid())

    parser = argparse.ArgumentParser()
    parser.add_argument('--restart-shares', action='store_true', help='Restart all active shares.')
    parser.add_argument('--verbose', '-v', action='store_true', help='Be verbose.')
    parser.add_argument('--database', '-d', action='store', help='Use the following database file.', default='')
    parser.add_argument('--manager-port', '-p', action='store', type=int,
                        help='The port the manager communicates on with it''s child processes.', default=-1)
    parser.add_argument('--server', '-s', action='store', type=str, default=DEFAULT_SERVER, help=argparse.SUPPRESS)
    parser.add_argument('--config-file', action='store', type=str, default='', help=argparse.SUPPRESS)
    parser.add_argument('--list', '-l', action='store_true', help="list shares and exit")
    parser.add_argument('--kill', '-k', action='store', type=int, help="Stop a share", default=0)
    parser.add_argument('--kill-all', '-K', action='store_true', help="Stop all shares")
    args = parser.parse_args()

    dbhandler.db_location = args.database

    if args.verbose:
        from logging import DEBUG
        set_log_level(DEBUG)
        logger.debug('You are seeing debug output.')
        Globals().verbose = True

    if args.manager_port not in xrange(-1, 65535):
        logger.error('--manager-port not in valid range [-1, 65535]')
        sys.exit(1)

  #   Globals().manager_port = args.manager_port
  #   Globals().openport_address = args.server
  #
  #   if args.config_file:
  #       Globals().config = args.config_file
  #
  #   manager = get_manager_instance()
  #
  #   logger.debug('db location: ' + dbhandler.db_location)
  #
  #   if args.list:
  #       manager.print_shares()
  #       sys.exit()
  #
  #   if args.kill:
  #       manager.kill(args.kill)
  #       sys.exit()
  #
  #   if args.kill_all:
  #       manager.kill_all()
  #       sys.exit()
  #
  #   get_and_save_manager_port(args.manager_port)
  # #  start_server_thread(onNewShare=manager.onNewShare)
  #
  #   sleep(1)
  #
  #   if args.restart_shares:
  #       manager.restart_sharing()

    def handleSigTERM(signum, frame):
        logger.debug('got a signal %s, frame %s going down' % (signum, frame))
        manager.exitApp(None)
    if not osinteraction.is_windows():
        signal.signal(signal.SIGTERM, handleSigTERM)
        signal.signal(signal.SIGINT, handleSigTERM)
    else:
        osinteraction.getInstance().handle_signals(handleSigTERM)

    while True:
        sleep(1)








class OpenportManagerService(object):
    def __init__(self, manager_port=-1, server='openport.io'):
        self.manager = get_manager_instance()
        Globals().manager_port = manager_port
        Globals().openport_address = server
        self.stopped = False

    def start(self, restart_shares=True):
        self.stopped = False

        get_and_save_manager_port()
      #  start_server_thread(onNewShare=self.manager.onNewShare)

        sleep(1)

        if restart_shares:
            self.manager.restart_sharing()

      #  def handleSigTERM(signum, frame):
      #      logger.debug('got a signal %s, frame %s going down' % (signum, frame))
      #      self.manager.exitApp(None)
      #  signal.signal(signal.SIGTERM, handleSigTERM)
      #  signal.signal(signal.SIGINT, handleSigTERM)

        while not self.stopped:
            sleep(1)

    def stop(self):
        self.stopped = True

if __name__ == '__main__':
    start_manager()
