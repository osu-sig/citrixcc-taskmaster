import os, sys, json, pprint
import yaml
import requests
from requests.auth import HTTPBasicAuth
from jinja2 import Environment, FileSystemLoader

pp = pprint.PrettyPrinter()
SCRIPTPATH = os.path.dirname(os.path.abspath(__file__))
JINENV = Environment(loader = FileSystemLoader('templates'))

with open(SCRIPTPATH + '/config.yml', 'r') as configfile:
    config = yaml.load(configfile.read())
    USERNAME = config['username']
    PASSWORD = config['password']
    ENDPOINT_BASE = config['endpoint_base']

def main(argv):
    with open(SCRIPTPATH + '/serviceobjects.yml', 'r') as servicefile:
        services = yaml.load(servicefile.read())['services']
    for service in services:
        for task in service['tasks']:
            create_task(task, service)

def create_task(taskname, service):
    template = JINENV.get_template('template_{}.yml'.format(taskname))
    payload = { 'ns_task': yaml.load(template.render(service=service)) }
    rc = call_api('configuration/ns_task', payload)
    if rc['errorcode'] == 400:
        print 'task {} already exists, re-creating it'.format(payload['ns_task']['name'])
        rcd = delete_task(payload['ns_task']['name'])
        if rcd['errorcode'] != 0:
            raise Exception('DELETE {0}{1} - errorcode: {2} {3}'.format(ENDPOINT_BASE, 'configuration/ns_task', rc['errorcode'], rc['message']))
        rcd = call_api('configuration/ns_task', payload)
        if rcd['errorcode'] != 0:
            raise Exception('failed to re-create task {}'.format(payload['ns_task']['name']))
    elif rc['errorcode'] != 0:
        raise Exception('POST {0}{1} - errorcode: {2} {3}'.format(ENDPOINT_BASE, 'configuration/ns_task', rc['errorcode'], rc['message']))
    else:
        print 'created task {}'.format(payload['ns_task']['name'])

def delete_task(taskname):
    endpoint = 'configuration/ns_task/{}'.format(taskname)
    resp = requests.delete(ENDPOINT_BASE + endpoint, auth=(USERNAME, PASSWORD))
    if resp.status_code != 200:
        raise Exception('DELETE {0}{1} {2}'.format(ENDPOINT_BASE, endpoint, resp.status_code))
    return resp.json()

def call_api(endpoint, payload):
    resp = requests.post(ENDPOINT_BASE + endpoint, json=payload, auth=(USERNAME, PASSWORD))
    if resp.status_code != 200:
        raise Exception('POST {0}{1} {2}'.format(ENDPOINT_BASE, endpoint, resp.status_code))
    return resp.json()

if __name__ == "__main__":
    main(sys.argv[1:])
