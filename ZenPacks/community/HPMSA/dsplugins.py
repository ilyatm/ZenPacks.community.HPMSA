from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import getPage
from pprint import pprint

from datetime import datetime
from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource import (
    PythonDataSourcePlugin,
    )
from Products.DataCollector.plugins.DataMaps import ObjectMap
from ZenPacks.community.HPMSA.msaapi import msaapi
import logging

LOG = logging.getLogger('zen.HPMSA')


class HPMSADS(PythonDataSourcePlugin):

    TAG = ''

    @classmethod
    def config_key(cls, datasource, context):
        return (
            context.device().id,
            datasource.getCycleTime(context),
            'hpmsa-health',
            )

    @classmethod
    def params(cls, datasource, context):
        return {
            'user': context.zHPMSAUser,
            'password': context.zHPMSAPassword,
            'controllers': context.zHPMSAControllers,
            'secure': context.zHPMSASecureConnection,
            'title': context.title,
            }

    def apiconnect(self, config):
        user = config.datasources[0].params['user']
        password = config.datasources[0].params['password']
        controllers = config.datasources[0].params['controllers']
        secure = config.datasources[0].params['secure']
        protocol = 'https' if secure else 'http'
        return msaapi(controllers, protocol, user, password, LOG)

    def collect(self, config):
        pass


class Conditions(HPMSADS):

    TAG = 'conditions'

    @inlineCallbacks
    def collect(self, config):
        api = self.apiconnect(config)
        url = api.get_url()
        data = self.new_data()
        if url is None:
            LOG.error('%s: Can\'t authenticate, check settings...', config)
            data['events'].append({
                'device': config.id,
                'severity': 'Error',
                'eventKey': 'hpmsa-conditions',
                'eventClassKey': 'hpmsa-conditions',
                'summary': 'Can not connect',
                'message': 'Can not authenticate, check settings...',
                })
            returnValue(None)
        else:
            headers = api.get_headers()
            devicemap = api.get_devicemap()
            results = {}
            for componentclass in devicemap.keys():
                cmd = devicemap[componentclass]['xml_obj_command']
                xml = yield getPage(url+cmd, headers=headers)

                results[componentclass] = api.get_conditions(xml, componentclass)

        for datasource in config.datasources:
            dt = datasource.template
            dc = datasource.component
            health = results[dt][dc]['health']
            healthreason = results[dt][dc]['health-reason']
            healthrecommendation = results[dt][dc]['health-recommendation']
            status = results[dt][dc]['status']
            compname = results[dt][dc]['compname']
            relname = results[dt][dc]['relname']
            modname = results[dt][dc]['modname']
            se = results[dt][dc]['modname']

            if compname:
                data['maps'].append(
                    ObjectMap({
                        'relname': relname,
                        'modname': modname,
                        'compname': compname,
                        'id': dc,
                        'health': health,
                        'status': status,
                        }))
            else:
                data['maps'].append(
                    ObjectMap({
                        'relname': relname,
                        'modname': modname,
                        'id': dc,
                        'health': health,
                        'status': status,
                        }))
            if health != 'OK':
                data['events'].append({
                    'device': config.id,
                    'component': datasource.component,
                    'severity': results[dt][dc]['severity'],
                    'eventKey': 'hpmsa-alert',
                    'eventClassKey': 'hpmsa-alert',
                    'summary': results[dt][dc]['health-reason'],
                    'message': results[dt][dc]['health-recommendation'],
                    })

        returnValue(data)
