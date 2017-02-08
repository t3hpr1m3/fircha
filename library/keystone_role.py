#!/usr/bin/env python

try:
	from keystoneauth1.identity import v3
	from keystoneauth1 import session
	from keystoneclient.v3 import client
except ImportError:
	keystoneclient_found = False
else:
	keystoneclient_found = True

class Role(object):
	def __init__(self, module):
		self.module          = module
		self.auth            = dict(
			url = module.params['auth_url'],
			token = module.params['auth_token'],
			username = module.params['auth_username'],
			password = module.params['auth_password']
		)

		self.name            = module.params['name']
		self.domain          = module.params['domain']
		self.state           = module.params['state']
		self.role            = None
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

	def _get_domain(self):
		for entry in self.keystone.domains.list():
			if entry.id == self.domain or entry.name == self.domain:
				return entry

		return None

	def _get_role(self):
		domain = None
		if self.domain:
			domain = self._get_domain()
			if domain is None:
				self.module.fail_json(msg="Invalid domain: %s" %
						self.domain)

		for entry in self.keystone.roles.list():
			if entry.name == self.name:
				if domain:
					if entry.domain == domain:
						return entry
				else:
					return entry

		return None

	def role_exists(self):
		self._authenticate()
		role = self._get_role()

		return role is not None

	def create_role(self):
		self._authenticate()
		domain = None
		if self.domain:
			domain = self._get_domain()
			if domain is None:
				self.module.fail_json(msg="Invalid domain: %s" %
						self.domain)

		kwargs = {}
		if domain:
			kwargs['domain'] = domain
		ks_role = self.keystone.roles.create(self.name, **kwargs)
		self.role = ks_role
		self.id = self.role.id

	def remove_role(self):
		self._authenticate()
		role = self._get_role()
		if role is not None:
			self.keystone.roles.delete(role)

def main():

	module = AnsibleModule(
		argument_spec = dict(
			name=dict(required=True, type='str'),
			domain=dict(required=False, type='str'),
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

	role = Role(module)
	changed = False
	result = {}

	if role.state == 'absent':
		if role.role_exists():
			if module.check_mode:
				module.exit_json(changed=True)
			role.remove_role()
			changed = True
	elif role.state == 'present':
		if not role.role_exists():
			if module.check_mode:
				module.exit_json(changed=True)
			role.create_role()
			changed = True
			result['id'] = role.id

	result['changed'] = changed

	module.exit_json(**result)

from ansible.module_utils.basic import *

if __name__ == '__main__':
	main()

