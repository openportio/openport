from sys import argv

def send_share_request(path, port):
    import urllib, urllib2

    url = 'http://127.0.0.1:%s' % port
    try:
        data = urllib.urlencode({'path' : path,})
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req).read()
        if response.strip() != 'ok':
            print response
    except Exception, detail:
        print "Err ", detail
        exit(9)

if __name__ == '__main__':
    send_share_request(argv[1], 8001)