#!/usr/bin/env python

import os
import sys
import argparse

try:
	import json
except ImportError:
	import simplejson as json

DEFAULT_INVENTORY = {
	"hosts": {
		"hulk": {
			"vars": {
				"ansible_ssh_hostname": "hulk.daprime.net",
				"ansible_ssh_user": "jdubz",
				"interface": "br-ex",
				"ipv4_address": "192.168.0.100",
				"openstack_cinder_volume_members": ["/dev/sdb"],
				"openstack_nova_volume_members": ["/dev/sdc"],
				"openstack_cinder_volume_targets": ["/dev/sda", "/dev/sdb", "/dev/sdc"]
			}
		}
	},
	"groups": {
		"memcached": {
			"hosts": ["hulk"]
		},
		"router": {
			"hosts": ["hulk"]
		},
		"database": {
			"hosts": ["hulk"]
		},
		"messaging": {
			"hosts": ["hulk"]
		},
		"controller": {
			"hosts": ["hulk"]
		},
		"compute_nodes": {
			"hosts": ["hulk"]
		},
		"ntp_servers": {
			"hosts": ["mars"]
		}
	}
}

class InventoryBuilder(object):

	def __init__(self, inventory_data):
		self.inventory = {}
		self.read_cli_args()

		if self.args.list:
			self.inventory = self.build_inventory(inventory_data)
		elif self.args.host:
			self.inventory = self.empty_inventory()
		else:
			self.inventory = self.empty_inventory()

		print json.dumps(self.inventory)

	def read_cli_args(self):
		parser = argparse.ArgumentParser()
		parser.add_argument('--list', action = 'store_true')
		parser.add_argument('--host', action = 'store')
		self.args = parser.parse_args()

	def build_inventory(self, inventory_data):
		hosts = inventory_data['hosts']
		groups = inventory_data['groups']
		inventory = {}
		for name, group in groups.iteritems():
			inventory[name] = group

		inventory['_meta'] = { 'hostvars': {} }

		for hostname, host in hosts.iteritems():
			inventory['_meta']['hostvars'][hostname] = host['vars']

		return inventory

	def empty_inventory(self):
		return { '_meta': { 'hostvars': {} } }

if __name__ == '__main__':
	InventoryBuilder(DEFAULT_INVENTORY)
