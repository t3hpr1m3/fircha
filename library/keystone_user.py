#!/usr/bin/env python

try:
	from keystoneauth1.identity import v3
	from keystoneauth1 import session
	from keystoneclient.v3 import client
except ImportError:
	keystoneclient_found = False
else:
	keystoneclient_found = True

class User(object):
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
		self.password        = module.params['password']
		self.email           = module.params['email']
		self.description     = module.params['description']
		self.enabled         = module.params['enabled']
		self.default_project = module.params['default_project']
		self.update_password = module.params['update_password']
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

	def _get_domain(self):
		if self.domain is None:
			return None

		for entry in self.keystone.domains.list():
			if entry.id == self.domain or entry.name == self.domain:
				return entry
		self.module.exit_json(failed=True, msg="Invalid domain: %s" %
				self.domain)

		return None

	def _get_project(self):
		if self.default_project is None:
			return None

		domain = self._get_domain()

		for entry in self.keystone.projects.list(domain=domain):
			if entry.id == self.default_project or entry.name == self.default_project:
				return entry

		self.module.exit_json(failed=True, msg="Invalid default_project: %s" % self.default_project)


	def _get_user(self):
		domain = self._get_domain()
		if domain is None:
			return None

		for entry in self.keystone.users.list(domain=domain):
			if entry.name == self.name:
				self.user = entry
				return entry

		return None

	def user_exists(self):
		self._authenticate()
		user = self._get_user()

		return user is not None

	def create_user(self):
		self._authenticate()
		project = self._get_project()

		domain = self._get_domain()
		if domain is None:
			self.module.fail_json(msg="Invalid domain: %s" %
					self.domain)

		ks_user = self.keystone.users.create(self.name,
				domain=domain, password=self.password,
				email=self.email,
				description=self.description,
				enabled=self.enabled, default_project=project)
		self.user = ks_user
		self.id = self.user.id

	def needs_update(self):
		self._authenticate()
		project = self._get_project()

		user = self._get_user()
		if user is None:
			return False

		if user.enabled != self.enabled:
			return True

		if self.update_password == 'always':
			return True

		return False

	def update_user(self):
		self._authenticate()
		project = self._get_project()

		user = self._get_user()
		if user is None:
			self.module.fail_json(msg="User does not exist")

		kwargs = {}
		if self.enabled is not None and user.enabled != self.enabled:
			kwargs['enabled'] = self.enabled
		if self.password is not None and self.update_password == 'always':
			kwargs['password'] = self.password

		if kwargs:
			ks_user = self.keystone.users.update(user, **kwargs)
			self.user = ks_user
			self.id = self.user.id

	def remove_user(self):
		self._authenticate()
		user = self._get_user()
		if user is not None:
			self.keystone.users.delete(user)

def main():

	module = AnsibleModule(
		argument_spec = dict(
			name=dict(required=True, type='str'),
			domain=dict(required=True, type='str'),
			password=dict(required=False, type='str'),
			email=dict(required=False, type='str'),
			description=dict(required=False, type='str'),
			enabled=dict(required=False, default=True, type='bool'),
			default_project=dict(required=False, type='str'),
			update_password=dict(default='always',
				choices=['always', 'on_create'], type='str'),
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

	user = User(module)
	changed = False
	result = {}

	if user.state == 'absent':
		if user.user_exists():
			if module.check_mode:
				module.exit_json(changed=True)
			user.remove_user()
			changed = True
	elif user.state == 'present':
		if not user.user_exists():
			if module.check_mode:
				module.exit_json(changed=True)
			user.create_user()
			changed = True
			result['id'] = user.id
		else:
			if user.needs_update():
				user.update_user()
				changed = True
				result['id'] = user.id

	result['changed'] = changed

	module.exit_json(**result)

from ansible.module_utils.basic import *

if __name__ == '__main__':
	main()

