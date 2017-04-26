import os, sys, json, pprint, argparse, re
import yaml
import requests
from requests.auth import HTTPBasicAuth
from jinja2 import Environment, FileSystemLoader

pp = pprint.PrettyPrinter()
SCRIPTPATH = os.path.dirname(os.path.abspath(__file__))
JINENV = Environment(loader = FileSystemLoader('templates'))

# load serviceobjects
with open(SCRIPTPATH + '/serviceobjects.yml', 'r') as servicefile:
    serviceobjects = yaml.load(servicefile.read())
services = serviceobjects['services']
groups = serviceobjects['groups']

# load configuration
with open(SCRIPTPATH + '/config.yml', 'r') as configfile:
    config = yaml.load(configfile.read())
    USERNAME = config['username']
    PASSWORD = config['password']
    ENDPOINT_BASE = config['endpoint_base']

# setup command line options
parser = argparse.ArgumentParser(description='Manage Citrix Command Center custom tasks')
group = parser.add_mutually_exclusive_group()
group.add_argument('-g', '--group', help='generate config values for provided group')
group.add_argument('-r', '--recreate', help='recreate tasks for provided service')
group.add_argument('-c', '--create', help='task to create (use name in Command Center, ex: lync_enable_server)')
group.add_argument('-d', '--delete', help='task to delete (use name in Command Center, ex: lync_enable_server)')
group.add_argument('--delete-all', action='store_true', help='delete all tasks in Command Center')
group.add_argument('--create-all', action='store_true', help='create all tasks in Command Center')
args = parser.parse_args()

# specify cipher set
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
try:
    requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST += 'HIGH:!DH:!aNULL'
except AttributeError:
    # no pyopenssl support used / needed / available
    pass

def main(argv):
    if args.recreate:
        recreate_service(args.recreate)
    elif args.create_all:
        create_all_tasks()
    elif args.delete_all:
        delete_all_tasks()
    elif args.create:
        create_task(args.create)
    elif args.delete:
        delete_task(args.delete)
    elif args.group:
        generate_group_config(args.group)
    else:
        parser.print_help()

def create_task(taskname):
    (target_service, target_tasksuffix) = parse_task_argument(taskname)

    found_task = False
    for service in services:
        if service['name'] == target_service and target_tasksuffix in service['tasks']:
            cc_create_task(target_tasksuffix, service)
            print 'created task {}_{}'.format(target_service, target_tasksuffix)
            found_task = True

    if not found_task:
        print 'task {}_{} not defined in serviceobjects.yml'.format(target_service, target_tasksuffix)

def delete_task(taskname):
    rcd = cc_delete_task(taskname)
    if rcd['errorcode'] != 0:
        raise Exception('DELETE {0}{1} - errorcode: {2} {3}'.format(ENDPOINT_BASE, 'configuration/ns_task', rc['errorcode'], rc['message']))
    else:
        print 'deleted task {}'.format(taskname)

def create_all_tasks():
    for service in services:
        for task in service['tasks']:
            cc_create_task(task, service)
            print 'created task {}_{}'.format(service['name'], task)

def delete_all_tasks():
    payload = { 'filter': 'classification:custom' }
    resp = requests.get(ENDPOINT_BASE + 'configuration/ns_task', params=payload, auth=(USERNAME, PASSWORD))
    result = resp.json()
    for task in result['ns_task']:
        if task['category'] != 'ADMIN_USE_ONLY':
            delete_task(task['name'])

def recreate_service(servicename):
    for service in services:
        if servicename != service['name']:
            continue
        print 'recreating tasks for {}...'.format(servicename)
        for task in service['tasks']:
            cc_create_task(task, service)
            print 'created task {}_{}'.format(servicename, task)

def generate_group_config(groupname):
    found_group = False
    for group in groups:
        if group['name'] == groupname:
            found_group = True

            lb_vservers = []
            servicegroups = []
            servers = []

            for target_service in group['services']:
                for service in services:
                    if target_service == service['name']:
                        lb_vservers.extend(service['lb_vservers'])
                        servicegroups.extend(service['servicegroups'])
                        for server in service['servers']:
                            servers.append(server['name'])

            print '   lb vservers: {}\n'.format(','.join(lb_vservers))
            print '   servicegroups: {}\n'.format(','.join(servicegroups))
            print '   servers: {}'.format(','.join(servers))

    if not found_group:
        print 'group {} not found in serviceobjects.yml'.format(groupname)

def cc_create_task(tasksuffix, service):
    template = JINENV.get_template('template_{}.yml'.format(tasksuffix))
    payload = { 'ns_task': yaml.load(template.render(service=service)) }
    rc = call_api('configuration/ns_task', payload)
    if rc['errorcode'] == 400:
        print 'task {} already exists, re-creating it'.format(payload['ns_task']['name'])
        rcd = cc_delete_task(payload['ns_task']['name'])
        if rcd['errorcode'] != 0:
            raise Exception('DELETE {0}{1} - errorcode: {2} {3}'.format(ENDPOINT_BASE, 'configuration/ns_task', rc['errorcode'], rc['message']))
        rcd = call_api('configuration/ns_task', payload)
        if rcd['errorcode'] != 0:
            raise Exception('failed to re-create task {}'.format(payload['ns_task']['name']))
    elif rc['errorcode'] != 0:
        raise Exception('POST {0}{1} - errorcode: {2} {3}'.format(ENDPOINT_BASE, 'configuration/ns_task', rc['errorcode'], rc['message']))

def cc_delete_task(taskname):
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

def parse_task_argument(arg):
    try:
        (s, t) = re.split('_', arg, 1)
    except ValueError:
        print 'ERROR: invalid task name'
        sys.exit(1)
    return (s, t)


if __name__ == "__main__":
    main(sys.argv[1:])
