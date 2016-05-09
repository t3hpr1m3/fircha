import re

def lvm_filter(drives):
	filters = []
	drives = list(drives)
	for drive in drives:
		groups = re.match('^.*\/([a-z]+)[0-9]*$', drive)
		if groups is not None:
			filters.append("\"a/%s/\"" % groups.group(1))

	return ", ".join(filters)

class FilterModule(object):
	filter_map = {
		'lvm_filter': lvm_filter
	}

	def filters(self):
		return self.filter_map
