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
                )
        except urllib2.URLError, e:
            log.warning(
                'Controller ip - %s, exception %s get next.',
                ip, e)
            continue

        response = ET.fromstring(keypage.read())[0][2].text

        if response != 'Authentication Unsuccessful':
            goodip = ip
            sessionkey = response
            # log.info("Controller ip - %s, got valid sessionkey", ip)
            break

    return goodip, sessionkey
