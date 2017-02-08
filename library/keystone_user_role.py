#!/usr/bin/env python

try:
	from keystoneauth1.identity import v3
	from keystoneauth1 import session
	from keystoneclient.v3 import client
except ImportError:
	keystoneclient_found = False
else:
	keystoneclient_found = True

class UserRole(object):
	def __init__(self, module):
		self.module          = module
		self.auth            = dict(
			url = module.params['auth_url'],
			token = module.params['auth_token'],
			username = module.params['auth_username'],
			password = module.params['auth_password']
		)

		self.user     = module.params['user']
		self.role     = module.params['role']
		self.project  = module.params['project']
		self.domain   = module.params['domain']
		self.state    = module.params['state']
		self.keystone = None
		self.service  = None
		self.id       = None

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
			self.module.fail_json(msg="%s" % e)

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
		if self.project is None:
			return None

		for entry in self.keystone.projects.list():
			if entry.id == self.project or entry.name == self.project:
				return entry

		self.module.fail_json(msg="Invalid project: %s" % self.project)

	def _get_role(self):
		if self.role is None:
			return None

		for entry in self.keystone.roles.list():
			if entry.id == self.role or entry.name == self.role:
				return entry

		self.module.fail_json(msg="Invalid role: %s" %
				self.role)

	def _get_user(self):

		for entry in self.keystone.users.list():
			if entry.name == self.user:
				return entry

		return None

	def _get_user_roles(self):
		user = self._get_user()
		roles = []
		return self.keystone.role_assignments.list(user=user)

	def user_has_role(self):
		self._authenticate()
		domain = self._get_domain()
		project = self._get_project()
		roles = self._get_user_roles()

		for role in self._get_user_roles():
			if domain is not None:
				if 'domain' in role.scope and role.scope['domain']['id'] == domain.id:
					return True
			elif project is not None:
				if 'project' in role.scope and role.scope['project']['id'] == project.id:
					return True

		return False

	def add_user_role(self):
		self._authenticate()
		domain = self._get_domain()
		project = self._get_project()
		role = self._get_role()
		user = self._get_user()
		if user is None:
			self.module.fail_json(msg="Invalid user: %s" % self.user)

		if domain is None and project is None:
			self.module.fail_json(msg="Neither domain or project is valid")

		if project is not None:
			self.keystone.roles.grant(role, user=user,
					project=project)
		elif domain is not None:
			self.keystone.roles.grant(role, user=user,
					domain=domain)

	def remove_user_role(self):
		self._authenticate()
		domain = self._get_domain()
		project = self._get_project()
		role = self._get_role()
		user = self._get_user()
		if user is None:
			self.module.fail_json("Invalid user: %s" % self.user)

		if project is not None:
			self.keystone.roles.revoke(role, user=user,
					project=project)
		elif domain is not None:
			self.keystone.roles.revoke(role, user=user,
					domain=domain)

def main():

	module = AnsibleModule(
		argument_spec = dict(
			user=dict(required=True, type='str'),
			role=dict(required=True, type='str'),
			domain=dict(required=False, type='str'),
			project=dict(required=False, type='str'),
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
				['auth_token', 'auth_password'],
				['domain', 'project']]
	)

	if not keystoneclient_found:
		module.fail_json(msg="the python-keystoneclient module is required.  Did you forget to install python-openstackclient?")

	if module.params['domain'] is None and module.params['project'] is None:
		module.fail_json(msg="Either domain or project is required")

	user_role = UserRole(module)
	changed = False
	result = {}

	if user_role.state == 'absent':
		if user_role.user_has_role():
			if module.check_mode:
				module.exit_json(changed=True)
			user_role.remove_role()
			changed = True
	elif user_role.state == 'present':
		if not user_role.user_has_role():
			if module.check_mode:
				module.exit_json(changed=True)
			user_role.add_user_role()
			changed = True
			result['id'] = user_role.id

	result['changed'] = changed

	module.exit_json(**result)

from ansible.module_utils.basic import *

if __name__ == '__main__':
	main()

