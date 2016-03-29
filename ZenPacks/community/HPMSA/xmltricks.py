import re

from Products.ZenUtils.Utils import prepId
from ZenPacks.community.HPMSA.schemas import device_map
import xml.etree.ElementTree as ET


def get_instance_statistic(xmlobj, compid, pattern):
    props = {}
    id = None

    for xmlprop in xmlobj.findall(".PROPERTY"):
        if xmlprop.attrib['name'] == compid:
            if pattern:
                m = re.search(pattern, xmlprop.text)
                if m:
                    id = m.group(1)
            else:
                id = xmlprop.text
        else:
            props[xmlprop.attrib['name']] = xmlprop.text
    return id, props


def apply_pattern(value, pattern):
    result = None
    if pattern:
        m = re.search(pattern, value)
        if m:
            result = prepId(m.group(1).upper())
    else:
        result = value
    return result


def get_product_version(xml):
    xml = ET.fromstring(xml)
    version = None
    for xmlprop in xml.findall("./OBJECT[@basetype='system']/.PROPERTY"):
        if xmlprop.attrib['name'] == 'product-id':
            version = xmlprop.text
    return version


def parsexml(xml, componentclass):
    xml = ET.fromstring(xml)
    xml_filter = device_map[componentclass]['xml_obj_filter']
    results = []
    for xml_object in xml.findall(xml_filter):
        properties = {}
        for xml_prop in xml_object.findall(".PROPERTY"):
            properties[xml_prop.attrib['name']] = xml_prop.text
        results.append(properties)
    return results


def get_relations(xml, componentclass):
    xml_relation = device_map[componentclass]['xml_obj_relation']
    xml_id = device_map[componentclass]['xml_obj_id']
    xml_rel_pattern = device_map[componentclass]['xml_obj_relation_pattern']
    xml_title = device_map[componentclass]['xml_obj_title']
    xml_attributes = device_map[componentclass]['xml_obj_attributes']

    components = parsexml(xml, componentclass)
    results = {}

    for component in components:
        relation = apply_pattern(component.get(xml_relation), xml_rel_pattern)
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


def get_health(xml, componentclass):
    severitys = {
        'Degraded': 'Error',
        'Fault': 'Critical',
        'Unknown': 'Warning',
        'N/A': 'Info',
        'OK': None,
        }
    xml_relation = device_map[componentclass]['xml_obj_relation']
    xml_id = device_map[componentclass]['xml_obj_id']
    xml_rel_pattern = device_map[componentclass]['xml_obj_relation_pattern']
    relname = device_map[componentclass]['relname']
    modname = device_map[componentclass]['modname']
    compname = device_map[componentclass]['compname']
    # xml_attributes = ['health', 'status', 'health-reason']

    components = parsexml(xml, componentclass)
    results = {}
    for component in components:
        id = component.get(xml_id)
        relation = apply_pattern(component.get(xml_relation), xml_rel_pattern)
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
        # if id in results:
        #     results[id].append(props)
        # else:
        #     results[id] = [props]

    return results
