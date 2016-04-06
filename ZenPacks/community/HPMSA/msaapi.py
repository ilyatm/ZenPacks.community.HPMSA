import hashlib
import urllib2
import yaml
import re
import os
import xml.etree.ElementTree as ET
from Products.ZenUtils.Utils import prepId
import pdb
from pprint import pprint

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


def get_devicemap():
    with open(os.path.dirname(__file__)+"/devicemap.yaml", 'r') as stream:
        try:
            return yaml.load(stream)
        except yaml.YAMLError as exc:
            return None


class msaapi:
    """HP MSA API Class """
    def __init__(self, iplist, protocol, user, password, log):
        self.errors = []
        auth = hashlib.md5(user+"_"+password).hexdigest()
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

    def get_msa_version(self, xml):
        xml = ET.fromstring(xml)
        version = None
        for xmlprop in xml.findall("./OBJECT[@basetype='system']/.PROPERTY"):
            if xmlprop.attrib['name'] == 'product-id':
                version = xmlprop.text

        return version

    def get_relation(self, xml, componentclass):
        devicemap = get_devicemap()
        xml_attrs = devicemap.get(componentclass)
        components = self.parsexml(xml, xml_attrs.get('xml_obj_filter'))
        results = {}
        for component in components:
            relation = self.apply_pattern(
                component.get(xml_attrs.get('xml_obj_relation'), ''),
                xml_attrs.get('xml_obj_relation_pattern'),
                )
            props = {
                'title': component.get(xml_attrs.get('xml_obj_title')),
                'id': prepId(component.get(xml_attrs.get('xml_obj_id'))),
            }
            for a in xml_attrs.get('xml_obj_attributes'):
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
        if pattern:
            m = re.search(pattern, value)
            if m:
                return prepId(m.group(1).upper())
        else:
            return value

    def get_conditions(self, xml, componentclass):
        devicemap = get_devicemap()
        xml_attrs = devicemap.get(componentclass)
        components = self.parsexml(xml, xml_attrs.get('xml_obj_filter'))
        results = {}
        for component in components:
            id = prepId(component.get(xml_attrs.get('xml_obj_id')))
            relation = self.apply_pattern(
                component.get(xml_attrs.get('xml_obj_relation'), ''),
                xml_attrs.get('xml_obj_relation_pattern'),
                )

            hrea = component.get(xml_attrs.get('health-reason'), '')
            hrec = component.get(xml_attrs.get('health-recommendation'), '')
            pdb.set_trace()
            props = {
                'compname': xml_attrs.get('compname', '') + relation,
                'modname': xml_attrs.get('modname'),
                'hrea': component.get('health-reason'),
                'hrec': component.get('health-recommendation'),
                'data': {
                    'id': id,
                    'relname': xml_attrs.get('relname'),
                },
            }
            for cond in xml_attrs.get('xml_obj_conditions'):
                props['data'].update({cond: component.get(cond)})

            results[id] = props

        return results
