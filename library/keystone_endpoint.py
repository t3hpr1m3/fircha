#!/usr/bin/env python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.pycompat24 import get_exception
try:
	from keystoneauth1.identity import v3
	from keystoneauth1 import session
	from keystoneclient.v3 import client
except ImportError:
	keystoneclient_found = False
else:
	keystoneclient_found = True

class Endpoint(object):
	def __init__(self, module):
		self.module       = module
		self.auth         = dict(
			url = module.params['auth_url'],
			token = module.params['auth_token'],
			username = module.params['auth_username'],
			password = module.params['auth_password']
		)

		self.url          = module.params['url']
		self.interface    = module.params['interface']
		self.service      = module.params['service']
		self.region       = module.params['region']
		self.state        = module.params['state']
		self.keystone     = None
		self.endpoint     = None
		self.id           = None

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
		for entry in self.keystone.services.list():
			if entry.name == self.service or entry.id == self.service:
				return entry

		return None

	def _get_endpoint(self):
		service = self._get_service()
		if service is None:
			return None

		for entry in self.keystone.endpoints.list(service=service,
				region=self.region):
			if entry.interface == self.interface:
				return entry

		return None

	def endpoint_exists(self):
		self._authenticate()
		endpoint = self._get_endpoint()

		return endpoint is not None

	def create_endpoint(self):
		self._authenticate()
		service = self._get_service()
		if service is None:
			self.module.fail_json(msg="Invalid service: %s" % self.service)

		ks_endpoint = self.keystone.endpoints.create(service=service,
			url=self.url, interface=self.interface,
			region=self.region)
		self.endpoint = ks_endpoint
		self.id = self.endpoint.id

	def needs_update(self):
		self._authenticate()
		endpoint = self._get_endpoint()
		if endpoint is None:
			return False
		return endpoint.url != self.url

	def update_endpoint(self):
		self._authenticate()
		service = self._get_service()
		if service is None:
			self.module.fail_json(msg="Invalid service: %s" %
					self.service)

		endpoint = self._get_endpoint()

		if endpoint is None:
			self.module.fail_json(msg="Endpoint does not exist")

		if endpoint.url != self.url:
			ks_endpoint = self.keystone.endpoints.update(endpoint,
					url=self.url)
			self.endpoint = ks_endpoint
			self.id = self.endpoint.id

	def remove_endpoint(self):
		self._authenticate()
		endpoint = self._get_endpoint()
		if endpoint is not None:
			self.keystone.endpoints.delete(endpoint)


def main():

	module = AnsibleModule(
		argument_spec = dict(
			url=dict(required=True),
			interface=dict(required=True),
			service=dict(required=True),
			region=dict(required=False, default='RegionOne'),
			state=dict(default='present', choices=['present', 'absent']),
			auth_url=dict(required=False, default='http://127.0.0.1:35357/v3'),
			auth_token=dict(required=False),
			auth_username=dict(required=False),
			auth_password=dict(required=False)
		),
		supports_check_mode=True,
		mutually_exclusive=[['auth_token', 'auth_username'],
				['auth_token', 'auth_password']]
	)

	if not keystoneclient_found:
		module.fail_json(msg="the python-keystoneclient module is required.  Did you forget to install python-openstackclient?")

	endpoint = Endpoint(module)
	changed = False
	result = {}

	if endpoint.state == 'absent':
		if endpoint.endpoint_exists():
			if module.check_mode:
				module.exit_json(changed=True)
			endpoint.remove_endpoint()
			changed = True
	elif endpoint.state == 'present':
		if not endpoint.endpoint_exists():
			if module.check_mode:
				module.exit_json(changed=True)
			endpoint.create_endpoint()
			changed = True
			result['id'] = endpoint.id
		else:
			if endpoint.needs_update():
				endpoint.update_endpoint()
				changed = True
				result['id'] = endpoint.id

	result['changed'] = changed

	module.exit_json(**result)

if __name__ == '__main__':
	main()
