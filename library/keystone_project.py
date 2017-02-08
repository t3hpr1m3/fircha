#!/usr/bin/env python

try:
	from keystoneauth1.identity import v3
	from keystoneauth1 import session
	from keystoneclient.v3 import client
except ImportError:
	keystoneclient_found = False
else:
	keystoneclient_found = True

class Project(object):
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
		self.domain          = module.params['domain']
		self.enabled         = module.params['enabled']
		self.state           = module.params['state']
		self.keystone        = None
		self.project         = None
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
			if entry.name == self.domain or entry.id == self.domain:
				return entry

		return None

	def _get_project(self):
		domain = self._get_domain()
		if domain is None:
			return None

		for entry in self.keystone.projects.list(domain=domain):
			if entry.name == self.name:
				return entry

		return None

	def project_exists(self):
		self._authenticate()
		project = self._get_project()

		return project is not None

	def create_project(self):
		self._authenticate()
		domain = self._get_domain()
		if domain is None:
			self.module.fail_json(msg="Invalid domain:%s" %
			self.domain)

		self.project = self.keystone.projects.create(self.name,
				domain, description=self.description,
				enabled=self.enabled)
		self.id = self.project.id

	def needs_update(self):
		self._authenticate()
		project = self._get_project()
		if project is None:
			return False

		if project.name != self.name:
			return True

		if project.enabled != self.enabled:
			return True

		if project.description != self.description:
			return True

		return False

	def update_project(self):
		self._authenticate()

		project = self._get_project()
		if project is None:
			self.module.fail_json(msg="Project does not exist")

		kwargs = {}
		if self.name is not None and project.name != self.name:
			kwargs['name'] = self.name
		if self.enabled is not None and project.enabled != self.enabled:
			kwargs['enabled'] = self.enabled
		if self.description is not None and project.description != self.description:
			kwargs['description'] = self.description

		if kwargs:
			ks_project = self.keystone.projects.update(project, **kwargs)
			self.project = ks_project
			self.id = self.project.id

	def remove_project(self):
		self._authenticate()
		project = self._get_project()
		if project is not None:
			self.keystone.projects.delete(project)

def main():

	module = AnsibleModule(
		argument_spec = dict(
			name=dict(required=True, type='str'),
			description=dict(required=False, type='str'),
			domain=dict(required=True, type='str'),
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

	project = Project(module)
	changed = False
	result = {}

	if project.state == 'absent':
		if project.project_exists():
			if module.check_mode:
				module.exit_json(changed=True)
			project.remove_project()
			changed = True
	elif project.state == 'present':
		if not project.project_exists():
			if module.check_mode:
				module.exit_json(changed=True)
			project.create_project()
			changed = True
			result['id'] = project.id
		else:
			if project.needs_update():
				project.update_project()
				changed = True
				result['id'] = project.id

	result['changed'] = changed

	module.exit_json(**result)

from ansible.module_utils.basic import *

if __name__ == '__main__':
	main()

