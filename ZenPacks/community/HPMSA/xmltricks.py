import re

from Products.ZenUtils.Utils import prepId
from ZenPacks.community.HPMSA.schemas import device_map
import xml.etree.ElementTree as ET


def get_health_status(xmlobj, id, relationId,
                      relationPattern, relname, modname, compname):
    props = {}
    relid = None

    for xmlprop in xmlobj.findall(".PROPERTY"):
        if xmlprop.attrib['name'] == relationId:
            if relationPattern:
                m = re.search(relationPattern, xmlprop.text)
                if m:
                    props['compname'] = compname + prepId(m.group(1).upper())
            else:
                props['compname'] = compname + xmlprop.text

        if xmlprop.attrib['name'] == id:
            relid = xmlprop.text
        if xmlprop.attrib['name'] == 'health-numeric':
            props['health-numeric'] = xmlprop.text
        if xmlprop.attrib['name'] == 'status-numeric':
            props['status-numeric'] = xmlprop.text

        props['relname'] = relname
        props['modname'] = modname
    return relid, props


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


def get_properties(xml, componentclass):
    relation = device_map[componentclass]['xml_obj_relation']
    id = device_map[componentclass]['xml_obj_id']
    attributes = device_map[componentclass]['xml_obj_attributes']
    pattern = device_map[componentclass]['xml_obj_relation_pattern']
    title = device_map[componentclass]['xml_obj_title']

    components = parsexml(xml, componentclass)
    results = {}

    for component in components:
        relid = apply_pattern(component.get(relation), pattern)
        props = {
            'title': component[title],
            'id': component[id],
        }
        for a in attributes:
            props.update({a: component[a]})

        if relid in results:
            results[relid].append(props)
        else:
            results[relid] = [props]

    return results
