import hashlib
import urllib2
import xml.etree.ElementTree as ET


def authMsa(controllers, protocol, user, password, log):
    auth = hashlib.md5(user+"_"+password).hexdigest()
    goodip = None
    sessionkey = None

    for ip in controllers:
        try:
            keypage = urllib2.urlopen(
                '{0}://{1}/api/login/{2}'.format(protocol, ip, auth),
                timeout=10
                ).read()

            response = ET.fromstring(keypage)[0][2].text

            if response != 'Authentication Unsuccessful':
                goodip = ip
                sessionkey = response
                # log.info("Controller ip - %s, got valid sessionkey", ip)
                break

        except urllib2.URLError, e:
            log.warning(
                'Controller ip - %s, exception %s trying next ip if exist...',
                ip, e)
            continue

    return goodip, sessionkey
