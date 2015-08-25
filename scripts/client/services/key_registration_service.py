import sys
import requests

from apps.keyhandling import get_or_create_public_key
from common.config import DEFAULT_SERVER


try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        print 'You need python 2.6 or simplejson to run this application.'
        sys.exit(1)


def register_key(args, server=DEFAULT_SERVER):
    if args.register_key:

        public_key = get_or_create_public_key()
        token = args.register_key

        url = "%s/linkKey" % server

        try:
            data = {
                'public_key': public_key,
                'key_binding_token': token}
            r = requests.post(url, data=data)
            dictionary = r.json()
            if 'status' not in dictionary or dictionary['status'] != 'ok':
                raise Exception('Did not get status ok: %s' % dictionary)
            print "key successfully registered"

        except Exception, detail:
            print "An error has occurred while communicating with the openport servers. ", detail
            if hasattr(detail, 'read'):
                print detail.read()
            raise detail

        sys.exit(0)
