import sys
import urllib
import urllib2
from apps.keyhandling import get_or_create_public_key
from manager.globals import DEFAULT_SERVER

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

        #TODO: https
        url = "http://%s/linkKey" % server

        try:
            data = urllib.urlencode({
                'public_key': public_key,
                'key_binding_token': token})
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req).read()
            dictionary = json.loads(response)
            if not 'status' in dictionary or dictionary['status'] != 'ok':
                raise Exception('Did not get status ok: %s' % dictionary)
            print "key successfully registered"

        except Exception, detail:
            print "An error has occurred while communicating the the openport servers. ", detail
            if hasattr(detail, 'read'):
                print detail.read()
            raise detail

        sys.exit(0)