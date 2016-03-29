from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import RelationshipMap, ObjectMap
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import getPage
from pprint import pprint
from ZenPacks.community.HPMSA.msaapi import msaapi


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
        self.device_map = api.get_devicemap()
        self.modeller_order = api.get_modeller_order()
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
                results['product_version'] = api.get_msa_version(xml)

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

            returnValue(results)

    def process(self, device, results, log):
        rm = []
        rm.append(ObjectMap({
            'product_version': results['product_version']
        }))
        for key in self.modeller_order:
            for itemid in results[key]:
                if itemid is not None:
                    rm.append(RelationshipMap(
                        compname=self.device_map[key]['compname']+itemid,
                        relname=self.device_map[key]['relname'],
                        modname=self.device_map[key]['modname'],
                        objmaps=results[key][itemid],
                        ))
                else:
                    rm.append(RelationshipMap(
                        relname=self.device_map[key]['relname'],
                        modname=self.device_map[key]['modname'],
                        objmaps=results[key][itemid],
                        ))
        return rm
