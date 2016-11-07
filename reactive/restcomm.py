import shutil

from subprocess import check_call

from charmhelpers.core import hookenv
from charmhelpers.core import unitdata

from charms import reactive
from charms.reactive import hook
from charms.reactive import when, when_not, when_any

db = unitdata.kv()
config = hookenv.config()

@hook('config-changed')
def config_changed():
    restart_if_need()

@hook('mysql-relation-changed')
def mysql_changed():
    restart_if_need()

def restart_if_need():
    if reactive.is_state('restcomm.started'):
        reactive.set_state('restcomm.changed')

@hook('api-relation-joined')
def config_changed():
    relation_set({'port': 8080})

@when('docker.available')
def install_restcomm():
    if reactive.is_state('restcomm.available'):
        return
    hookenv.status_set('maintenance', 'Pulling Restcomm-Connect')
    check_call(['docker', 'pull', 'restcomm/restcomm:stable'])

    # open ports: HTTP, SIP, RTP
    hookenv.open_port(8080, 'TCP')
    hookenv.open_port(5080, 'UDP')
    hookenv.open_port('65000-65535', 'UDP')

    reactive.set_state('restcomm.available')

@when_any('restcomm.available', 'restcomm.changed')
@when_not('restcomm.started')
def start_restcomm():
    adminPassword = config.get('init_password')
    voiceRssKey = config.get('voicerss_key')
    configUrl = config.get('config_url')
    outboundProxy = config.get('outbound_proxy')
    smsOutboundProxy = config.get('sms_outbound_proxy')

    mysqlHost = ''
    mysqlSchema = ''
    mysqlUser = ''
    mysqlPswd = ''

    mysqlRelationIds = hookenv.relation_ids('mysql')
    if len(mysqlRelationIds) > 0 :
        mysqlRelationId = mysqlRelationIds[0]
        mysqlHost = hookenv.relation_get(mysqlRelationId, 'host')
        mysqlSchema = hookenv.relation_get(mysqlRelationId, 'database')
        mysqlUser = hookenv.relation_get(mysqlRelationId, 'user')
        mysqlPswd = hookenv.relation_get(mysqlRelationId, 'password')

    run_command = [
        'docker',
        'run',
        '--restart', 'always',
        '--name', 'restcomm',
        '--net', 'host',
        '-e', 'ENVCONFURL={}'.format(configUrl),
        '-e', 'MYSQL_HOST={}'.format(mysqlHost),
        '-e', 'MYSQL_USER={}'.format(mysqlUser),
        '-e', 'MYSQL_PASSWORD={}'.format(mysqlPswd),
        '-e', 'MYSQL_SCHEMA={}'.format(mysqlSchema),
        '-e', 'OUTBOUND_PROXY={}'.format(outboundProxy),
        '-e', 'SMS_OUTBOUND_PROXY={}'.format(smsOutboundProxy),
        '-e', 'INITIAL_ADMIN_PASSWORD={}'.format(adminPassword),
        '-e', 'VOICERSS_KEY={}'.format(voiceRssKey),
        '-e', 'MEDIASERVER_LOGS_LOCATION={}'.format('media_server'),
        '-e', 'EDIASERVER_LOWEST_PORT={}'.format('65000'),
        '-e', 'MEDIASERVER_HIGHEST_PORT={}'.format('65535'),
        '-e', 'LOG_LEVEL={}'.format('DEBUG'),
        '-e', 'RESTCOMM_LOGS={}'.format('/var/log/restcomm'),
        '-e', 'CORE_LOGS_LOCATION={}'.format('restcomm_core'),
        '-e', 'RESTCOMM_TRACE_LOG={}'.format('restcomm_trace'),
        '-e', 'RVD_LOCATION={}'.format('/opt/restcomm-rvd-workspace'),
        '-v', '{}:{}'.format('/var/log/restcomm/', '/var/log/restcomm/'),
        '-v', '{}:{}'.format('/opt/restcomm-rvd-workspace/', '/opt/restcomm-rvd-workspace/'),
        '-d',
        'restcomm/restcomm:stable'
    ]
    reactive.set_state('restcomm.started')