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

import ast, json, logging, linecache, get_file_list
from python_compat import imap, lchain, lmap


def main():
	enums = []
	enums_use_hash = {}
	config_calls = []
	for (fn, _) in get_file_list.get_file_list(show_external=False,
			show_aux=False, show_script=False, show_testsuite=False, show_type_list=['py']):
		if 'scriptlets' in fn:
			continue
		_process_calls_in_file(fn, enums, enums_use_hash, config_calls)

	for result in config_calls:
		result['args'] = lmap(_parse_option_spec, result['node'].args)
		result['kwargs'] = {}
		for keyword in result['node'].keywords:
			result['kwargs'][keyword.arg] = _parse_option_spec(keyword.value)
		result['api'] = result['fqfn'].split('.')[-1]
		result['scope'] = result['fqfn'].split('.')[-2]
		result['pargs'] = result['kwargs'].pop('pargs', '<impossible>')
		result['on_change'] = result['kwargs'].pop('on_change', '<impossible>')
		result['on_valid'] = result['kwargs'].pop('on_valid', '<no validation>')
		result['persistent'] = result['kwargs'].pop('persistent', False)
		result.pop('node')

	fp = open('docgen_config_calls.json', 'w')
	json.dump(config_calls, fp, indent=2, sort_keys=True)
	fp.close()

	fp = open('docgen_enums.json', 'w')
	assert len(enums) == len(dict(enums))
	json.dump({'enums': dict(enums), 'use_hash': enums_use_hash}, fp, indent=2, sort_keys=True)
	fp.close()


class ConfigVisitor(ast.NodeVisitor):
	def __init__(self):
		ast.NodeVisitor.__init__(self)
		self._caller_stack = []
		self._stack = []
		self.calls = []

	def generic_visit(self, node):
		self._stack.append(node)
		ast.NodeVisitor.generic_visit(self, node)
		self._stack.pop()

	def visit_Call(self, node):  # pylint:disable=invalid-name
		self.calls.append((list(self._caller_stack), node, list(self._stack)))
		self.generic_visit(node)

	def visit_ClassDef(self, node):  # pylint:disable=invalid-name
		self._caller_stack.append(node.name)
		self.generic_visit(node)
		self._caller_stack.pop()

	def visit_FunctionDef(self, node):  # pylint:disable=invalid-name
		self._caller_stack.append(node.name)
		self.generic_visit(node)
		self._caller_stack.pop()


def _analyse_file(fn):
	try:
		tree = ast.parse(open(fn).read())
	except Exception:
		logging.warning(fn)
		raise
	visitor = ConfigVisitor()
	visitor.visit(tree)
	return (tree, visitor.calls)


def _get_func_name(node):
	if isinstance(node, ast.Name):
		result = node.id
	elif isinstance(node, ast.Attribute):
		result = _get_func_name(node.value) + '.' + node.attr
	elif isinstance(node, ast.Call):
		result = _get_func_name(node.func) + '(...)'
	elif isinstance(node, ast.Subscript):
		result = _get_func_name(node.value) + '[...]'
	elif isinstance(node, (ast.BinOp, ast.BoolOp)):
		result = '<operation>'
	elif isinstance(node, ast.Str):
		result = '<some string>'
	elif isinstance(node, ast.Lambda):
		result = '<lambda>'
	else:
		result = '???'
	return result


def _join_config_locations(*opt_list):
	opt_first = opt_list[0]
	opt_list = opt_list[1:]
	if isinstance(opt_first, (list, tuple)):  # first option is a list - expand the first parameter
		if not opt_list:  # only first option -> clean and return
			return lmap(str.strip, opt_first)
		return lchain(imap(lambda opt: _join_config_locations(opt.strip(), *opt_list), opt_first))
	if not opt_list:  # only first option -> clean and return
		return [opt_first.strip()]

	def _do_join(opt):
		return (opt_first + ' ' + opt).strip()
	return lmap(_do_join, _join_config_locations(*opt_list))


def _parse_option_call(value):
	args_list = []
	for parg in imap(_parse_option_spec, value.args):
		if isinstance(parg, (list, tuple)):
			args_list.append(lmap(lambda x: x.strip().strip('"').strip("'"), parg))
		else:
			args_list.append(parg.strip().strip('"').strip("'"))

	if isinstance(value.func, ast.Name):
		if value.func.id == '_get_handler_option':
			return _join_config_locations('<name:logger_name>', ['', '<name:handler_name>'], *args_list)
		elif value.func.id == 'join_config_locations':
			return _join_config_locations(*args_list)
	elif isinstance(value.func, ast.Attribute):
		if value.func.attr == '_get_pproc_opt':
			return _join_config_locations(['', '<name:datasource_name>'], 'partition', *args_list)
		if value.func.attr == '_get_part_opt':
			return _join_config_locations(['', '<name:datasource_name>'], *args_list)
		elif value.func.attr == '_get_dproc_opt':
			return _join_config_locations('<name:datasource_name>', *args_list)
	arg_str = str.join(', ', imap(str, imap(_parse_option_spec, value.args)))
	return '<call:%s(%s)>' % (_get_func_name(value.func), arg_str)


def _parse_option_name(value):
	if value.id == 'True':
		return True
	elif value.id == 'False':
		return False
	elif value.id == 'None':
		return None
	return '<name:%s>' % value.id


def _parse_option_op(value):
	value_left = _parse_option_spec(value.left)
	value_right = _parse_option_spec(value.right)
	if isinstance(value.op, ast.Add):
		return '%s %s' % (
			value_left.strip().rstrip("'").strip(),
			value_right.strip().lstrip("'").strip())
	elif isinstance(value.op, ast.Mod):
		value_left = value_left.replace('%d', '%s')
		try:
			return value_left % value_right
		except Exception:
			return value_left + '%' + value_right
	elif isinstance(value.op, ast.Mult):
		return eval('%s * %s' % (value_left, value_right))  # pylint:disable=eval-used


def _parse_option_spec(value):
	if isinstance(value, ast.Str):
		result = repr(value.s)
	elif isinstance(value, ast.Num):
		result = value.n
	elif isinstance(value, ast.Name):
		result = _parse_option_name(value)
	elif isinstance(value, ast.Attribute):
		result = '<attr:%s>' % value.attr.strip('_')
	elif isinstance(value, (ast.List, ast.Tuple)):
		return lmap(_parse_option_spec, value.elts)
	elif isinstance(value, ast.Dict):
		key_value_iter = zip(imap(_parse_option_spec, value.keys), imap(_parse_option_spec, value.values))
		result = '{%s}' % str.join(', ', imap(lambda k_v: '%s: %s' % k_v, key_value_iter))
	elif isinstance(value, ast.Call):
		result = _parse_option_call(value)
	elif isinstance(value, ast.BinOp):
		result = _parse_option_op(value) or '<manual>'
	elif isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.USub):
		result = -_parse_option_spec(value.operand)
	elif hasattr(ast, 'NameConstant') and isinstance(value, getattr(ast, 'NameConstant')):
		result = value.value
	else:
		result = '<manual>'
	return result


def _process_calls_in_file(fn, enums, enums_use_hash, config_calls):
	(_, call_infos) = _analyse_file(fn)
	for (caller_stack, node, parents) in call_infos:
		result = _transform_call(fn, caller_stack, node)

		is_pconfig_get = ('self.get' in result['fqfn']) and (result['fn'].endswith('pconfig.py'))

		if 'make_enum' in result['fqfn']:
			if 'make_enum.enum_list' in result['fqfn']:
				continue
			_process_enum(node, parents, result, enums, enums_use_hash)
			continue

		elif '_query_config' in result['fqfn']:
			result['fqfn'] = _get_func_name(node.args[0])
			node.args = node.args[1:]
			config_calls.append(result)

		elif 'config.is_interactive' in result['fqfn']:
			config_calls.append(result)

		elif is_pconfig_get or ('config.get' in result['fqfn']):
			if is_pconfig_get:
				result['fqfn'] = result['fqfn'].replace('self.get', 'pconfig.get')
			assert result['node'].func.attr.startswith('get')  # prevent sequential calls with get
			use = True
			for key in ['get_config', 'get_work_path', 'get_state', 'get_option_list']:  # internal API
				if key in result['fqfn']:
					use = False
			if use:
				config_calls.append(result)


def _process_enum(node, parents, result, enums, enums_use_hash):
	if len(node.args) == 1:
		enum_name = parents[-1].targets[0].id
	elif len(node.args) == 2:
		enum_name = node.args[1].id

	def _iter_kw():
		for entry in result['node'].keywords:
			try:
				value = entry.value.id
			except Exception:  # API change
				value = str(entry.value.value)
			yield (entry.arg, value)
	kw_list = list(_iter_kw())
	enums_use_hash[enum_name] = ('use_hash', 'False') not in kw_list
	try:
		enums.append((enum_name, lmap(lambda x: x.s, node.args[0].elts)))
	except Exception:
		enums.append((enum_name, '<manual>'))


def _transform_call(fn, caller_stack, node):
	result = {'fn': fn, 'lineno': node.lineno, 'line': linecache.getline(fn, node.lineno),
		'fqfn': _get_func_name(node.func), 'node': node, 'callers': caller_stack}
	assert '???' not in result['fqfn']
	return result


if __name__ == '__main__':
	main()
