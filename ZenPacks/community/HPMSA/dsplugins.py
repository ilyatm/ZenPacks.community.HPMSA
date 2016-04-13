import logging
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import getPage
from datetime import datetime
from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource import (
    PythonDataSourcePlugin,
    )
from Products.DataCollector.plugins.DataMaps import ObjectMap
from ZenPacks.community.HPMSA.msaapi import msaapi, get_devicemap
from time import time
from datetime import datetime


LOG = logging.getLogger('zen.HPMSA')


class HPMSADS(PythonDataSourcePlugin):

    TAG = ''

    @classmethod
    def config_key(cls, datasource, context):
        return (
            context.device().id,
            datasource.getCycleTime(context),
            'hpmsa-{tag}'.format(tag=cls.TAG),
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
    severities = {
        'Degraded': 'Error',
        'Fault': 'Critical',
        'Unknown': 'Warning',
        'N/A': 'Info',
        'OK': None,
        }

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
            devicemap = get_devicemap()
            results = {}
            for cc, props in devicemap.items():
                cmd = props.get('xml_obj_command')
                try:
                    xml = yield getPage(url+cmd, headers=headers)
                except Exception, e:
                    LOG.error("%s: %s", device.id, e)
                if xml:
                    results[cc] = api.get_conditions(xml, cc)

        for datasource in config.datasources:
            dt = datasource.template
            dc = datasource.component

            data['maps'].append(ObjectMap(
                data=results[dt][dc]['data'],
                compname=results[dt][dc]['compname'],
                modname=results[dt][dc]['modname'],
                ))

            health = results[dt][dc]['data']['health']
            severity = self.severities[health]
            if health != 'OK':
                data['events'].append({
                    'device': config.id,
                    'component': datasource.component,
                    'severity': self.severities[health],
                    'eventKey': 'hpmsa-conditions',
                    'eventClassKey': 'hpmsa',
                    'summary': results[dt][dc]['hrea'],
                    'message': results[dt][dc]['hrec'],
                    })

        returnValue(data)


class Events(HPMSADS):

    TAG = 'Events'
    severities = {
        '0': 'Info',
        '1': 'Warning',
        '2': 'Error',
        '3': 'Critical',
        }

    @inlineCallbacks
    def collect(self, config):
        api = self.apiconnect(config)
        url = api.get_url()
        data = self.new_data()
        ts = time()
        dt = datetime.fromtimestamp(ts).strftime('%m%d%y%H%M%S')
        df = datetime.fromtimestamp(ts-86400).strftime('%m%d%y%H%M%S')
        if url is None:
            LOG.error('%s: Can\'t authenticate, check settings...', config)
            data['events'].append({
                'device': config.id,
                'severity': 'Error',
                'eventKey': 'hpmsa-conditions',
                'eventClassKey': 'hpmsa',
                'summary': 'Can not connect',
                'message': 'Can not authenticate, check settings...',
                })
            returnValue(None)
        else:
            headers = api.get_headers()
            try:
                xml = yield getPage(
                    url+"events/from/{0}/to/{1}".format(df, dt),
                    headers=headers
                    )
            except Exception, e:
                LOG.error("%s: %s", device.id, e)
            if xml:
                events = api.get_events(xml)
                for evt in events:
                    data['events'].append({
                        'device': config.id,
                        'severity': self.severities[evt['severity-numeric']],
                        'eventKey': 'hpmsa-event-'+evt['event-id'],
                        'eventClassKey': 'hpmsa',
                        'summary': evt['message'],
                        'message': "{0} {1} {2}".format(
                            evt['message'],
                            evt['additional-information'],
                            evt['recommended-action'],
                            )
                    })

        returnValue(data)


class Statistics(HPMSADS):

    TAG = 'Statistics'

    statistics_map = [
        'Controller',
        'HardDisk',
        'HostPort',
        'Volume',
        'VirtualDisk',
    ]

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
            devicemap = get_devicemap()
            results = {}
            for cc in self.statistics_map:
                cmd = devicemap.get(cc).get('xml_stat_command')
                try:
                    xml = yield getPage(url+cmd, headers=headers)
                except Exception, e:
                    LOG.error(e)
                if xml:
                    results[cc] = api.get_statistics(xml, cc)

        for datasource in config.datasources:
            dt, dc = datasource.template, datasource.component
            for dp in datasource.points:
                val = results.get(dt, {}).get(dc, {}).get(dp.id)
                if val:
                    data['values'][dc][dp.id] = val

        returnValue(data)
