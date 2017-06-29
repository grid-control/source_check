import logging, get_file_list
from grid_control.utils.file_tools import SafeFile


def main():
	for (fn, fnrel) in get_file_list.get_file_list(show_type_list=['py'],
			show_external=True, show_testsuite=False):
		ident_map = {}
		for line in SafeFile(fn).iter_close():
			ident = line.replace(line.lstrip(), '')
			ident_level = ident.count('\t')
			line = line.strip()
			if line.startswith('def ') or line.startswith('class '):
				ident_map[ident_level] = line.split(':')[0]
				for other_ident_level in list(ident_map):
					if other_ident_level > ident_level:
						ident_map.pop(other_ident_level)
			parent = ident_map.get(ident_level - 1, '')
			if line.startswith('def ') and parent.startswith('def '):
				if not line.startswith('def _'):
					logging.warning('%r %r', fnrel, ident_map)


if __name__ == '__main__':
	main()
