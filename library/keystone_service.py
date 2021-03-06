#!/usr/bin/env python

try:
	from keystoneauth1.identity import v3
	from keystoneauth1 import session
	from keystoneclient.v3 import client
except ImportError:
	keystoneclient_found = False
else:
	keystoneclient_found = True

class Service(object):
	def __init__(self, module):
		self.module          = module
		self.auth            = dict(
			url = module.params['auth_url'],
			token = module.params['auth_token'],
			username = module.params['auth_username'],
			password = module.params['auth_password']
		)

		self.name            = module.params['name']
		self.description     = module.params['description']
		self.type            = module.params['type']
		self.enabled         = module.params['enabled']
		self.state           = module.params['state']
		self.keystone        = None
		self.service         = None
		self.user            = None
		self.id              = None

	def _authenticate(self):
		if self.auth['token']:
			auth = v3.Password(auth_url=self.auth['url'],
					token=self.auth['token'],
					project_name='admin',
					user_domain_id='default',
					project_domain_id='default')
		else:
			auth = v3.Password(auth_url=self.auth['url'],
					username=self.auth['username'],
					password=self.auth['password'],
					project_name='admin',
					user_domain_id='default',
					project_domain_id='default')

		sess = session.Session(auth=auth)

		try:
			self.keystone = client.Client(session=sess)
		except Exception:
			e = get_exception()
			self.module.exit_json(failed=True, msg="%s" % e)


	def _get_service(self):
		services = self.keystone.services.list(type=self.type)
		if services:
			return services[0]

		return None

	def service_exists(self):
		self._authenticate()
		service = self._get_service()

		return service is not None

	def create_service(self):
		self._authenticate()

		self.service = self.keystone.services.create(name=self.name,
				type=self.type, description=self.description,
				enabled=self.enabled)
		self.id = self.service.id

	def needs_update(self):
		self._authenticate()
		service = self._get_service()
		if service is None:
			return False

		if service.name != self.name:
			return True

		if service.enabled != self.enabled:
			return True

		if service.description != self.description:
			return True

		return False

	def update_service(self):
		self._authenticate()

		service = self._get_service()
		if service is None:
			self.module.fail_json(msg="Service does not exist")

		kwargs = {}
		if self.name is not None and service.name != self.name:
			kwargs['name'] = self.name
		if self.enabled is not None and service.enabled != self.enabled:
			kwargs['enabled'] = self.enabled
		if self.description is not None and service.description != self.description:
			kwargs['description'] = self.description

		if kwargs:
			ks_service = self.keystone.services.update(service, **kwargs)
			self.service = ks_service
			self.id = self.service.id

	def remove_service(self):
		self._authenticate()
		service = self._get_service()
		if service is not None:
			self.keystone.services.delete(service)

def main():

	module = AnsibleModule(
		argument_spec = dict(
			name=dict(required=True, type='str'),
			description=dict(required=False, type='str'),
			type=dict(default=None, type='str'),
			enabled=dict(required=False, default=True, type='bool'),
			state=dict(default='present', choices=['present',
			'absent']),
			auth_url=dict(required=False,
				default='http://127.0.0.1:35357/v3', type='str'),
			auth_token=dict(required=False, type='str'),
			auth_username=dict(required=False, type='str'),
			auth_password=dict(required=False, type='str')
		),
		supports_check_mode=True,
		mutually_exclusive=[['auth_token', 'auth_username'],
				['auth_token', 'auth_password']]
	)

	if not keystoneclient_found:
		module.fail_json(msg="the python-keystoneclient module is required.  Did you forget to install python-openstackclient?")

	service = Service(module)
	changed = False
	result = {}

	if service.state == 'absent':
		if service.service_exists():
			if module.check_mode:
				module.exit_json(changed=True)
			service.remove_service()
			changed = True
	elif service.state == 'present':
		if not service.service_exists():
			if module.check_mode:
				module.exit_json(changed=True)
			service.create_service()
			changed = True
			result['id'] = service.id
		else:
			if service.needs_update():
				service.update_service()
				changed = True
				result['id'] = service.id

	result['changed'] = changed

	module.exit_json(**result)

from ansible.module_utils.basic import *

if __name__ == '__main__':
	main()

