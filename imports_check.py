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

import logging, get_file_list
from python_compat import any, ifilter, imap, set


def main():
	for (fn, fnrel) in get_file_list.get_file_list(show_type_list=['py'],
			show_external=False, show_aux=False):
		logging.debug(fnrel)
		_check_usage(fnrel, open(fn).read())


def _check_dupe_libs(fn, list_source):
	if len(set(list_source)) != len(list_source):
		logging.warning('%s duplicated libs! %r', fn, _get_dupes(list_source))


def _check_imported_use(fn, list_from, code_str):
	# remove import lines for usage check
	def _is_import_or_comment(line):
		line = line.lstrip()
		return line.startswith('#') or line.startswith('from ') or line.startswith('import ')

	code_str = str.join('\n', ifilter(
		lambda line: not _is_import_or_comment(line), code_str.splitlines()))

	for imported in list_from:
		if ' as ' in imported:
			imported = imported.split(' as ')[1]

		def _chk(fmt):
			code_piece = fmt % imported
			return code_piece in code_str

		if any(imap(_chk, ['%s(', '%s.', 'raise %s', '(%s)', '=%s', ' = %s', ' != %s', 'return %s',
			', %s)', '(%s, ', 'except %s', ' %s,', '\t%s,', '%s, [', '%s]', 'or %s', '%s not in'])):
			continue
		if imported in ['backends', 'datasets']:
			continue
		logging.warning('%s superflous %r', fn, imported)


def _check_usage(fn, raw):
	code_str = raw.replace('def set(', '')

	list_imported = _get_imported_libs(code_str)
	_find_dupe_imports(fn, list_imported)
	_find_unused_modules(fn, list_imported, code_str)

	if fn.endswith('__init__.py'):
		return

	(list_from, list_source) = _get_imported(fn, code_str)
	_check_dupe_libs(fn, list_source)
	_check_imported_use(fn, list_from, code_str)


def _find_dupe_imports(fn, list_imported):
	if len(set(list_imported)) != len(list_imported):
		logging.warning('%s duplicated libs! %r', fn, _get_dupes(list_imported))


def _find_unused_modules(fn, list_imported, code_str):
	for lib in list_imported:
		lib = lib.split('#')[0].strip()

		def _chk(pat):
			return (pat % lib) not in code_str
		if (lib != 'testfwk') and _chk('%s.') and _chk('= %s\n') and _chk('getattr(%s') and _chk('(%s, '):
			logging.warning('%s superflous %r', fn, lib)


def _get_dupes(value):
	value_set = set(value)
	value_list = list(value)
	while value_set:
		value_list.remove(value_set.pop())
	return value_list


def _get_imported(fn, code_str):
	list_from = []
	list_source = []
	for import_line in ifilter(lambda line: line.lstrip().startswith('from '), code_str.splitlines()):
		if 'import ' not in import_line:
			continue
		if '*' in import_line:
			logging.warning('%s wildcard import!', fn)
		else:
			if (len(import_line.split('#')[0].strip()) <= 100) and ('#' in import_line):
				logging.warning('%s invalid marker!', fn)
			import_line = import_line.split('#')[0].strip()
			list_from.extend(imap(str.strip, import_line.split('import ')[1].split(',')))
			list_source.append(import_line.split('import ')[0].strip().split()[1])
	return (list_from, list_source)


def _get_imported_libs(code_str):
	list_imported = []
	iter_imports = ifilter(lambda line: line.lstrip().startswith('import '), code_str.splitlines())
	for import_line in iter_imports:
		import_line = import_line.split('#')[0].strip()
		list_imported.extend(imap(str.strip, import_line.replace('import ', '').split(',')))
	return list_imported


if __name__ == '__main__':
	main()
