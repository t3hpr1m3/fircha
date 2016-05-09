#!/usr/bin/env python

try:
	from keystoneclient.v2_0 import client
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

def ensure_endpoint_exists(keystone, publicurl, internalurl,
		adminurl, region, service_name, check_mode):

	service_id = get_service(keystone, service_name).id

	try:
		endpoint = get_endpoint(keystone=keystone, publicurl=publicurl,
				internalurl=internalurl, adminurl=adminurl,
				region=region, service_id=service_id)
	except KeyError:
		pass
	else:
		return False, endpoint.id

	if check_mode:
		return True, None

	ks_service = keystone.endpoints.create(service_id=service_id,
			publicurl=publicurl, internalurl=internalurl,
			adminurl=adminurl, region=region)

	return True, ks_service.id

def ensure_endpoint_absent(keystone, publicurl, internalurl, adminurl, region,
		service_name, check_mode):

	service_id = get_service(keystone, service_name).id

	if not endpoint_exists(keystone=keystone, publicurl=publicurl,
			internalurl=internalurl, adminurl=adminurl,
			region=region, service_id=service_id):
		return False

	if check_mode:
		return True

	endpoint = get_endpoint(keystone=keystone, publicurl=publicurl,
			internalurl=internalurl, adminurl=adminurl,
			region=region, service_id=service_id)
	keystone.endpoints.delete(endpoint.id)

def endpoint_match(endpoint, publicurl, internalurl, adminurl, region,
		service_id):

	return endpoint.publicurl == publicurl and \
			getattr(endpoint, 'internalurl') == internalurl and \
			getattr(endpoint, 'adminurl') == adminurl and \
			endpoint.region == region and \
			endpoint.service_id == service_id

def endpoint_exists(keystone, publicurl, internalurl, adminurl, region,
		service_id):
	endpoints = [x for x in keystone.endpoints.list() if endpoint_match(x,
		publicurl, internalurl, adminurl, region, service_id)]

	return any(endpoints)

def get_service(keystone, service_name):
	services = [x for x in keystone.services.list() if x.name == service_name]
	count = len(services)
	if count == 0:
		raise KeyError("No keystone services with name: %s" % service_name)
	elif count > 1:
		raise ValueError("%d services with name %s" % (count, service_name))
	else:
		return services[0]

def get_endpoint(keystone, publicurl, internalurl, adminurl, region,
		service_id):
	endpoints = [x for x in keystone.endpoints.list() if endpoint_match(x,
		publicurl, internalurl, adminurl, region, service_id)]

	count = len(endpoints)

	if count == 0:
		raise KeyError(
				"No keystone endpoint with publicurl: %s, "
				"internalurl: %s, adminurl: %s, region: %s, "
				"service_id: %s" % (publicurl, internalurl,
					adminurl, region, service_id))
	elif count > 1:
		raise ValueError(
				"%d services with publicurl: %s, "
				"internalurl: %s, adminurl: %s, region: %s, "
				"service_id: %s" % (count, publicurl, internalurl,
					adminurl, region, service_id))
	else:
		return endpoints[0]


def main():
	argument_spec = openstack_argument_spec()
	argument_spec.update(dict(
		publicurl=dict(required=True),
		internalurl=dict(required=True),
		adminurl=dict(required=True),
		region=dict(required=False, default='RegionOne'),
		service_name=dict(required=True),
		state=dict(default='present', choices=['present', 'absent']),
		endpoint=dict(required=False,
		default='http://127.0.0.1:35357/v3'),
		token=dict(required=False),
		login_user=dict(required=False),
		login_password=dict(required=False),
		login_tenant_name=dict(required=False)
	))

	module = AnsibleModule(
		argument_spec=argument_spec,
		supports_check_mode=True,
		mutually_exclusive=[['token', 'login_user'],
				['token', 'login_password'],
				['token', 'login_tenant_name']]
	)

	if not keystoneclient_found:
		module.fail_json(msg="the python-keystoneclient module is required.  Did you forget to install python-openstackclient?")

	publicurl               = module.params['publicurl']
	internalurl             = module.params['internalurl']
	adminurl                = module.params['adminurl']
	service_name            = module.params['service_name']
	region                  = module.params['region']
	service_name            = module.params['service_name']
	state                   = module.params['state']
	endpoint                = module.params['endpoint']
	token                   = module.params['token']
	login_user              = module.params['login_user']
	login_password          = module.params['login_password']
	login_tenant_name       = module.params['login_tenant_name']

	keystone = authenticate(endpoint=endpoint, token=token,
			login_user=login_user,
			login_password=login_password,
			login_tenant_name=login_tenant_name)

	check_mode = module.check_mode

	id = None

	try:
		if state == 'present':
			changed, id = ensure_endpoint_exists(keystone=keystone,
					publicurl=publicurl,
					internalurl=internalurl,
					adminurl=adminurl,
					region=region,
					service_name=service_name,
					check_mode=check_mode)

		elif state == 'absent':
			changed = ensure_endpoint_absent(keystone=keystone,
					publicurl=publicurl,
					internalurl=internalurl,
					adminurl=adminurl,
					region=region,
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
