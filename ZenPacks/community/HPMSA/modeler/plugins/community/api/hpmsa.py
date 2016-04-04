from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import RelationshipMap, ObjectMap
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import getPage
from pprint import pprint
from ZenPacks.community.HPMSA.msaapi import (
    msaapi,
    get_devicemap,
    modeller_order,
    )
import pdb


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

        api = msaapi(controllers, protocol, user, password, log)

        results = {}

        if api.get_url() is None:
            returnValue(None)
        else:
            url = api.get_url()
            headers = api.get_headers()
            try:
                xml = yield getPage(url+'system', headers=headers)
            except Exception, e:
                log.error("%s: %s", device.id, e)

            if xml:
                results['product-id'] = api.get_msa_version(xml)

            self.device_map = get_devicemap()
            for componentclass in self.device_map:
                cmd = self.device_map[componentclass]['xml_obj_command']
                try:
                    xml = yield getPage(url+cmd, headers=headers)
                except Exception, e:
                    log.error("%s: %s", device.id, e)
                if xml:
                    results[componentclass] = api.get_relation(
                        xml, componentclass
                        )
            # pprint(results)
            returnValue(results)

    def process(self, device, results, log):
        rm = []
        rm.append(ObjectMap({
            'product-id': results['product-id']
        }))
        for key in modeller_order:
            m = results.get(key)
            for r, c in m.items():
                if r:
                    rm.append(RelationshipMap(
                        compname=self.device_map[key]['compname']+r,
                        relname=self.device_map[key]['relname'],
                        modname=self.device_map[key]['modname'],
                        objmaps=c,
                        ))
                else:
                    rm.append(RelationshipMap(
                        relname=self.device_map[key]['relname'],
                        modname=self.device_map[key]['modname'],
                        objmaps=c,
                        ))
        return rm
