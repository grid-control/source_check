import os, sys, logging, get_file_list
from python_compat import any, imap, lmap, sorted


def main():
	stored_sys_path = list(sys.path)
	available_imports = {}
	used_imports = {}
	for (fn, fnrel) in get_file_list.get_file_list(show_type_list=['py'],
			show_external=True, show_aux=False, show_testsuite=False):
		logging.debug(fnrel)
		blacklist = ['/requests/', 'python_compat_', 'commands.py']
		if fn.endswith('go.py') or any(imap(lambda pat: pat in fn, blacklist)):
			continue
		for line in open(fn):
			if ('import' in line) and ('from' in line):
				import_lines = lmap(str.strip, line.split('import')[1].split(','))
				import_src = line.split('from')[1].split('import')[0].strip()
				used_imports.setdefault(import_src, []).extend(import_lines)

		module = None
		if ('/scripts/' in fn) and not fn.endswith('gc_scripts.py'):
			continue
		elif fn.endswith('__init__.py'):
			sys.path.append(os.path.dirname(os.path.dirname(fn)))
			module = __import__(os.path.basename(os.path.dirname(fn)))
		else:
			sys.path.append(os.path.dirname(fn))
			module = __import__(os.path.basename(fn).split('.')[0])
		if hasattr(module, '__all__'):
			mod_all = list(module.__all__)
			mod_sort = sorted(mod_all, key=str.lower)
			available_imports[module] = mod_sort
			if mod_all != mod_sort:
				logging.warning('%s %s', fn, module)
				logging.warning('unsorted:')
				logging.warning('  - %s', mod_all)
				logging.warning('  + %s', mod_sort)
		sys.path = list(stored_sys_path)
	_display_unused_exports(used_imports, available_imports)


def _display_unused_exports(used_imports, available_imports):
	for (module, export_list) in available_imports.items():
		for export in export_list:
			for (import_src, import_list) in used_imports.items():
				if import_src.endswith(module.__name__):
					import_count = import_list.count(export)
					if import_count < 2:
						logging.warning('export use count %d %30s : %s', import_count, import_src, export)


if __name__ == '__main__':
	main()
