import logging, get_file_list
from grid_control.utils.file_tools import SafeFile
from python_compat import any, imap


def main():
	for (fn, fnrel) in get_file_list.get_file_list(show_type_list=['py'],
			show_external=True, show_testsuite=False):
		ident_map = {}
		blacklist = ['python_compat.py', '/htcondor_wms/', 'xmpp']
		if any(imap(lambda name: name in fn, blacklist)):
			continue
		for line in SafeFile(fn).iter_close():
			ident = line.replace(line.lstrip(), '')
			ident_level = ident.count('\t')
			line = line.strip()
			if line.startswith('def ') or line.startswith('class '):
				ident_map[ident_level] = line.split(':')[0]
				for other_ident_level in list(ident_map):
					if other_ident_level > ident_level:
						ident_map.pop(other_ident_level)
			parent_ident = ident_level - 1
			while (parent_ident not in ident_map) and (parent_ident > 0):
				parent_ident = parent_ident - 1
			parent = ident_map.get(parent_ident, '')
			if line.startswith('def ') and parent.startswith('def '):
				if not line.startswith('def _'):
					logging.warning('nested function missing prefix: %r %r', fnrel, ident_map)


if __name__ == '__main__':
	main()
