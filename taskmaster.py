import os, sys, json, pprint
import yaml
import requests
from requests.auth import HTTPBasicAuth

pp = pprint.PrettyPrinter()
SCRIPTPATH = os.path.dirname(os.path.abspath(__file__))

try:
    configfile = open(SCRIPTPATH + '/config.yml', 'r')
except IOError:
    print 'Missing config file config.yml'
    sys.exit()
else:
    config = yaml.load(configfile.read())
    USERNAME = config['username']
    PASSWORD = config['password']
    ENDPOINT_BASE = config['endpoint_base']

def main(argv):
    taskfile = open(SCRIPTPATH + '/templates/template_enable_server.yml', 'r')
    task = yaml.load(taskfile.read())
    task['name'] = task['name'].format('testo')
    payload = { 'ns_task': task }
    rc = call_api('configuration/ns_task', payload)
    if rc['errorcode'] != 0:
        raise Exception('POST {0}{1} - errorcode: {2} {3}'.format(ENDPOINT_BASE, 'configuration/ns_task', rc['errorcode'], rc['message']))
    else:
        print 'created task {}'.format(task['name'])

def call_api(endpoint, payload):
    resp = requests.post(ENDPOINT_BASE + endpoint, json=payload, auth=(USERNAME, PASSWORD))
    if resp.status_code != 200:
        raise Exception('POST {0}{1} {2}'.format(ENDPOINT_BASE, endpoint, resp.status_code))
    return resp.json()

if __name__ == "__main__":
    main(sys.argv[1:])
