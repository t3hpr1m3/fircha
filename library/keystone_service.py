#!/usr/bin/env python

try:
	from keystoneclient.v3 import client
except ImportError:
	keystoneclient_found = False
else:
	keystoneclient_found = True


def authenticate(endpoint, token, login_user, login_password,
		login_tenant_name):

	if token:
		return client.Client(endpoint=endpoint, token=token)
	else:
		return client.Client(auth_url=endpoint, username=login_user,
							password=login_password,
							tenant_name=login_tenant_name)

def service_exists(keystone, service_name):
	return service_name in [x.name for x in keystone.services.list()]

def get_service(keystone, service_name):
	services = [x for x in keystone.services.list() if x.name == service_name]
	count = len(services)
	if count == 0:
		raise KeyError("No keystone services with name: %s" % service_name)
	elif count > 1:
		raise ValueError("%d services with name %s" % (count, service_name))
	else:
		return services[0]

def get_service_id(keystone, service_name):
	return get_service(keystone, service_name).id

def ensure_service_exists(keystone, service_name, service_type,
	service_description, check_mode):

	try:
		service = get_service(keystone=keystone,
			service_name=service_name)
	except KeyError:
		pass
	else:
		return False, service.id

	if check_mode:
		return True, None

	ks_service = keystone.services.create(name=service_name,
						service_type=service_type,
						description=service_description)

	return True, ks_service.id

def ensure_service_absent(keystone, service_name, check_mode):
	if not service_exists(keystone=keystone, service_name=service_name):
		return False

	if check_mode:
		return True

	service = get_service(keystone=keystone, service_name=service_name)
	keystone.services.delete(service.id)


def main():
	#
	# Define the arguments
	#
	argument_spec = openstack_argument_spec()
	argument_spec.update(dict(
		name=dict(required=True),
		service_type=dict(required=True),
		description=dict(required=False, default="Not Provided"),
		state=dict(default='present', choices=['present', 'absent']),
		endpoint=dict(required=False, default="http://127.0.0.1:35357/v2.0"),
		token=dict(required=False),
		login_user=dict(required=False),
		login_password=dict(required=False),
		login_tenant_name=dict(required=False)
	))

	#
	# Set up the ansible interface
	#
	module = AnsibleModule(
		argument_spec=argument_spec,
		supports_check_mode=True,
		mutually_exclusive=[['token', 'login_user'],
					['token', 'login_password'],
					['token', 'login_tenant_name']]
	)

	if not keystoneclient_found:
		module.fail_json(msg="the python-keystoneclient module is required.  Did you forget to install python-openstackclient?")

	#
	# Prepare the keystone arguments
	#
	service_name = module.params['name']
	service_type = module.params['service_type']
	service_description = module.params['description']
	state = module.params['state']
	endpoint = module.params['endpoint']
	token = module.params['token']
	login_user = module.params['login_user']
	login_password = module.params['login_password']
	login_tenant_name = module.params['login_tenant_name']

	#
	# Instantiate the keystone client
	#
	keystone = authenticate(endpoint=endpoint, token=token,
			login_user=login_user,
			login_password=login_password,
			login_tenant_name=login_tenant_name)

	check_mode = module.check_mode

	id = None
	try:
		if state == 'present':
			changed, id = ensure_service_exists(
					keystone=keystone,
					service_name=service_name,
					service_type=service_type,
					service_description=service_description,
					check_mode=check_mode)
		elif state == 'absent':
			changed = ensure_service_absent(keystone=keystone,
											service_name=service_name,
											check_mode=check_mode)
		else:
			raise ValueError("Invalid state: %s" % state)

	except Exception, e:
		if check_mode:
			module.exit_json(changed=True, msg="exception: %s" % e)
		else:
			module.fail_json(msg="exception: %s" % e)
	else:
		module.exit_json(changed=changed, id=id)


from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *

if __name__ == '__main__':
	main()
