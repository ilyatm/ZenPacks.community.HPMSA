from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import RelationshipMap, ObjectMap
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import getPage
from pprint import pprint
from ZenPacks.community.HPMSA.schemas import (
    device_map,
    modeller_order,
    )
from ZenPacks.community.HPMSA.msaauth import authMsa
from ZenPacks.community.HPMSA.xmltricks import (
    get_product_version,
    get_properties,
    )


class hpmsa(PythonPlugin):

    ZENPACKID = 'Zenpacks.rni.HPMSA'

    requiredProperties = (
        'zHPMSAControllers',
        'zHPMSAUser',
        'zHPMSAPassword',
        'zHPMSASecureConnection',
        )

    deviceProperties = PythonPlugin.deviceProperties + requiredProperties

    @inlineCallbacks
    def collect(self, device, log):

        log.info("%s: collecting data", device.id)

        controllers = getattr(device, 'zHPMSAControllers', None)
        if not controllers:
            log.error("%s: %s not set.", device.id, 'zHPMSAControllers')
            returnValue(None)

        user = getattr(device, 'zHPMSAUser', None)
        if not user:
            log.error("%s: %s not set.", device.id, 'zHPMSAUser')
            returnValue(None)

        password = getattr(device, 'zHPMSAPassword', None)
        if not password:
            log.error("%s: %s not set.", device.id, 'zHPMSAPassword')
            returnValue(None)

        secure = getattr(device, 'zHPMSASecureConnection', None)
        protocol = 'https' if secure else 'http'

        ip, sessionkey = authMsa(controllers, protocol, user, password, log)

        results = {}

        if ip is None:
            log.error('%s can\'t authenticate...', device.id)
            returnValue(None)
        else:
            msa_version = yield getPage(
                '{0}://{1}/api/show/{2}'
                .format(protocol, ip, 'system'),
                headers={"sessionKey": "{0}".format(sessionkey)}
                )

            version = get_product_version(msa_version)
            results['product_version'] = version
            for componentclass in device_map.keys():
                cmd = device_map[componentclass]['xml_obj_command']
                xml = yield getPage(
                    '{0}://{1}/api/show/{2}'
                    .format(protocol, ip, cmd),
                    headers={"sessionKey": '{0}'.format(sessionkey)}
                    )
                results[componentclass] = get_properties(xml, componentclass)

            returnValue(results)

    def process(self, device, results, log):
        rm = []
        rm.append(ObjectMap({
            'product_version': results['product_version']
        }))
        for key in modeller_order:
            for itemid in results[key]:
                if itemid is not None:
                    rm.append(RelationshipMap(
                        compname=device_map[key]['compname']+itemid,
                        relname=device_map[key]['relname'],
                        modname=device_map[key]['modname'],
                        objmaps=results[key][itemid],
                        ))
                else:
                    rm.append(RelationshipMap(
                        relname=device_map[key]['relname'],
                        modname=device_map[key]['modname'],
                        objmaps=results[key][itemid],
                        ))
        return rm
