import hashlib
import urllib2
import yaml
import re
import os
import xml.etree.ElementTree as ET
from Products.ZenUtils.Utils import prepId


class msaapi:
    """HP MSA API Class """
    modeller_order = [
        'Enclosure',
        'Controller',
        'VirtualDisk',
        'PowerSupp',
        'HardDisk',
        'Volume',
        'HostPort',
        'ExpansionPort',
        'ManagementPort',
        'InoutModule',
        'CompactFlash'
    ]

    def __init__(self, iplist, protocol, user, password, log):
        auth = hashlib.md5(user+"_"+password).hexdigest()

        with open(os.path.dirname(__file__)+"/devicemap.yaml", 'r') as stream:
            try:
                self.devicemap = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.errors = []
        for ip in iplist:
            try:
                url = '{0}://{1}/api/login/{2}'.format(protocol, ip, auth)
                keypage = urllib2.urlopen(url, timeout=10)

            except urllib2.URLError, e:
                log.error('Controller ip - {0}, \
                            exception {1} get next.'.format(ip, e))
                continue

            response = ET.fromstring(keypage.read())[0][2].text

            if response != 'Authentication Unsuccessful':
                self.url = '{0}://{1}/api/show/'.format(protocol, ip)
                self.headers = {"sessionKey": response}
                break
            else:
                log.error("{0}. Check username, password.".format(response))

    def get_url(self):
        return self.url

    def get_headers(self):
        return self.headers

    def get_devicemap(self):
        return self.devicemap

    def get_modeller_order(self):
        return self.modeller_order

    def get_msa_version(self, xml):
        xml = ET.fromstring(xml)
        version = None
        for xmlprop in xml.findall("./OBJECT[@basetype='system']/.PROPERTY"):
            if xmlprop.attrib['name'] == 'product-id':
                version = xmlprop.text

        return version

    def get_relation(self, xml, componentclass):
        cc = self.devicemap[componentclass]
        xml_relation = cc['xml_obj_relation']
        xml_id = cc['xml_obj_id']
        xml_rel_pattern = cc['xml_obj_relation_pattern']
        xml_title = cc['xml_obj_title']
        xml_attributes = cc['xml_obj_attributes']
        xml_obj_filter = cc['xml_obj_filter']

        components = self.parsexml(xml, xml_obj_filter)
        results = {}

        for component in components:
            relation = self.apply_pattern(
                component.get(xml_relation), xml_rel_pattern
                )
            props = {
                'title': component.get(xml_title),
                'id': component.get(xml_id),
            }
            for a in xml_attributes:
                props.update({a: component.get(a)})

            if relation in results:
                results[relation].append(props)
            else:
                results[relation] = [props]

        return results

    def parsexml(self, xml, xml_obj_filter):

        xml = ET.fromstring(xml)
        results = []
        for xml_object in xml.findall(xml_obj_filter):
            properties = {}
            for xml_prop in xml_object.findall(".PROPERTY"):
                properties[xml_prop.attrib['name']] = xml_prop.text
            results.append(properties)

        return results

    def apply_pattern(self, value, pattern):
        result = None
        if pattern:
            m = re.search(pattern, value)
            if m:
                result = prepId(m.group(1).upper())
        else:
            result = value

        return result

    def get_conditions(self, xml, componentclass):
        severitys = {
            'Degraded': 'Error',
            'Fault': 'Critical',
            'Unknown': 'Warning',
            'N/A': 'Info',
            'OK': None,
            }
        cc = self.devicemap[componentclass]
        xml_relation = cc['xml_obj_relation']
        xml_id = cc['xml_obj_id']
        xml_rel_pattern = cc['xml_obj_relation_pattern']
        relname = cc['relname']
        modname = cc['modname']
        compname = cc['compname']
        xml_obj_filter = cc['xml_obj_filter']

        components = self.parsexml(xml, xml_obj_filter)
        results = {}
        for component in components:
            id = component.get(xml_id)
            relation = self.apply_pattern(
                component.get(xml_relation), xml_rel_pattern
                )
            cmpname = compname + relation if compname else None
            props = {
                'compname': cmpname,
                'relname': relname,
                'modname': modname,
                'health': component.get('health'),
                'health-reason': component.get('health-reason'),
                'health-recommendation': component.get('health-recommendation'),
                'status': component.get('status'),
                'severity': severitys[component.get('health')]
            }
            results[id] = props

        return results
