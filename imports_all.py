# | Copyright 2017 Karlsruhe Institute of Technology
# |
# | Licensed under the Apache License, Version 2.0 (the "License");
# | you may not use this file except in compliance with the License.
# | You may obtain a copy of the License at
# |
# |     http://www.apache.org/licenses/LICENSE-2.0
# |
# | Unless required by applicable law or agreed to in writing, software
# | distributed under the License is distributed on an "AS IS" BASIS,
# | WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# | See the License for the specific language governing permissions and
# | limitations under the License.

import os, sys, logging, get_file_list
from python_compat import any, imap, lfilter, lmap, sorted


def main():
	stored_sys_path = list(sys.path)
	available_imports = {}
	used_imports = {}
	for (fn, fnrel) in get_file_list.get_file_list(show_type_list=['py'],
			show_external=False, show_aux=False, show_testsuite=False):
		logging.debug(fnrel)
		blacklist = ['/requests/', 'python_compat_', 'commands.py']
		if fn.endswith('go.py') or any(imap(lambda pat: pat in fn, blacklist)):
			continue
		imported_in_file = []
		for line in open(fn):
			if ('import' in line) and ('from' in line):
				import_lines = lmap(str.strip, line.split('import')[1].split(','))
				import_src = line.split('from')[1].split('import')[0].strip()
				imported_in_file.extend(import_lines)
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
		else:
			available_imports[module] = _get_module_functions(module, imported_in_file)
		sys.path = list(stored_sys_path)
	_display_unused_exports(used_imports, available_imports)


def _display_unused_exports(used_imports, available_imports):
	warning_list = []
	for (module, export_list) in available_imports.items():
		for export in export_list:
			for (import_src, import_list) in used_imports.items():
				if import_src.endswith('.' + module.__name__) or (import_src == module.__name__):
					import_count = import_list.count(export)
					if import_count < 2:
						warning_list.append((import_count, import_src, export))
	for (import_count, import_src, export) in sorted(warning_list):
		logging.warning('export use count %d %40s : %s', import_count, import_src, export)


def _get_module_functions(module, imported_in_file):
	mod_all = dir(module)
	mod_fun = lfilter(lambda name: type(getattr(module, name)).__name__ == 'function', mod_all)
	mod_public_fun = lfilter(lambda name: name[0].islower() and not name.startswith('_'), mod_fun)
	return lfilter(lambda name: name not in imported_in_file, mod_public_fun)


if __name__ == '__main__':
	main()
