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

import sys, json
from python_compat import identity, imap, lfilter, lidfilter, lmap, set, sorted


def main():
	config_call_list = _get_json('docgen_config_calls.json')
	plugin_infos = _get_json('docgen_plugin_infos.json')
	available_plugins = _get_available_plugins(plugin_infos)

	user_dict = _get_json('docgen_user.json')
	user_location_list = user_dict['location_whitelist'] + user_dict['location_blacklist']
	_rewrite_user_dict(user_dict)

	enum_info_dict = _get_enum_info_dict(user_dict, _get_json('docgen_enums.json')['enums'])

	opt_to_cc_list = _get_opt_to_cc_list(config_call_list,
		available_plugins, enum_info_dict, plugin_infos)

	user_key_used = set()
	used_remap = set()

	_apply_user_to_cc_list(opt_to_cc_list, user_dict, user_key_used, used_remap, available_plugins)
	cc_by_location = _get_cc_by_location(user_dict, opt_to_cc_list, used_remap)

	for location in [True]:
		# for location in cc_by_location:
		_output('grid-control options')
		_output('====================')
		_output('')
		for location in user_dict['location_whitelist']:
			_display_location_deep(location, cc_by_location, user_dict, plugin_infos, enum_info_dict)

		def _sort_by_inheritance(location):
			return (tuple(plugin_infos.get(location, {}).get('bases', [])), location)
		for location in sorted(cc_by_location, key=_sort_by_inheritance):
			if location not in user_location_list:
				_display_location_deep(location, cc_by_location, user_dict, plugin_infos, enum_info_dict)

	for entry in sorted(user_dict['options']):
		if entry not in user_key_used:
			_output('Unused: %r %r' % (entry, user_dict['options'][entry]))
			_output('')


def _apply_user_to_cc(cfg_call, user_dict, user_key_used, used_remap, available_plugins):
	user_key_used.add(cfg_call['option'])
	cfg_call['output_altopt'] = ''
	if len(cfg_call['options']) > 1:
		cfg_call['output_altopt'] = ' / %s' % str.join(' / ', cfg_call['options'][1:])
	cfg_call['option_display'] = cfg_call['option']
	tmp = dict(user_dict['option_map'])
	tmp.update(cfg_call.get('option_map', {}))
	cfg_call['option_map'] = tmp
	for entry in cfg_call['option_map']:
		new_entry_str = cfg_call['option_map'][entry]
		cfg_call['option_display'] = cfg_call['option_display'].replace(entry, new_entry_str)
		cfg_call['output_altopt'] = cfg_call['output_altopt'].replace(entry, new_entry_str)
	cfg_call.update(user_dict['api'][cfg_call['api']])
	cfg_call.update(user_dict['options'].get(cfg_call['option'], {}))
	user_key_used.add(cfg_call['option'] + ':' + cfg_call['location'])
	cfg_call.update(user_dict['options'].get(cfg_call['option'] + ':' + cfg_call['location'], {}))
	if cfg_call['location'] in user_dict['location_remap']:
		used_remap.add(cfg_call['location'])
		cfg_call['location'] = user_dict['location_remap'][cfg_call['location']]

	opl_fmt = user_dict['format']['output_plugin_list']
	cfg_call['available_filter_list'] = str.join('',
		imap(lambda value: opl_fmt % value, sorted(available_plugins['ListFilter'])))
	cfg_call['available_matcher_list'] = str.join('',
		imap(lambda value: opl_fmt % value, sorted(available_plugins['Matcher'])))
	cfg_call['available_parameter_parser'] = str.join('',
		imap(lambda value: opl_fmt % value, sorted(available_plugins['ParameterParser'])))
	cfg_call['available_parameter_tuple_parser'] = str.join('',
		imap(lambda value: opl_fmt % value, sorted(available_plugins['ParameterTupleParser'])))
	if cfg_call.get('available'):
		cfg_call['available_list'] = str.join('',
			imap(lambda value: opl_fmt % value, sorted(cfg_call['available'])))
	if cfg_call.get('available_multi'):
		cfg_call['available_multi_list'] = str.join('',
			imap(lambda value: opl_fmt % value, sorted(cfg_call['available_multi'])))

	if 'cls_bases' in cfg_call:
		plugin_info = None
		for cls_base in cfg_call['cls_bases']:
			plugin_info = user_dict['plugin_details'].get(cls_base, plugin_info)
		cfg_call['plugin_singular'] = plugin_info[0]
		cfg_call['plugin_plural'] = plugin_info[1]

	cfg_call['output_default'] = ''
	if cfg_call['default'] is not None:
		default = str(cfg_call['default']).strip()
		for call in cfg_call.get('call', []):
			default = default.replace('<call:%s>' % call, cfg_call['call'][call])
		default_map = cfg_call.get('default_map', {})
		for key in default_map:
			if key not in default:
				raise Exception('Unused default map: %r = %r\n%r' % (key, default_map[key], default))
		default = default_map.get(default, default)
		cfg_call['output_default'] = user_dict['format']['output_default'] % default
	cfg_call['user_text'] = cfg_call.get('user_text', '') % cfg_call
	cfg_call['append_options'] = _get_sub_cc(cfg_call, cfg_call.get('append_options', []))
	cfg_call['prepend_options'] = _get_sub_cc(cfg_call, cfg_call.get('prepend_options', []))


def _apply_user_to_cc_list(opt_to_cc_list, user_dict, user_key_used, used_remap, available_plugins):
	# Apply user documentation
	opt_to_cc = {}
	for opt in opt_to_cc_list:
		for cfg_call in opt_to_cc_list[opt]:
			if len(opt_to_cc_list[opt]) > 1:
				user_specs = user_dict['options'].get(cfg_call['option'])
				if user_specs and not user_specs.get('disable_dupe_check', False):
					raise Exception('User option %s is not specific enough! %s' % (cfg_call['options'],
						json.dumps(opt_to_cc_list[opt], indent=2)))
			opt_to_cc[opt] = cfg_call
			_apply_user_to_cc(cfg_call, user_dict, user_key_used, used_remap, available_plugins)
	return opt_to_cc


def _display_location(location_list, cc_by_location, user_dict, enum_info_dict):
	if '.' in location_list[0]:
		_output(json.dumps(cc_by_location.get(location_list[0]), indent=2))
		raise Exception('Invalid location %r' % location_list[0])
	_output('.. _%s:' % location_list[0])
	_output('%s options' % location_list[0])
	_output('-' * len('%s options' % location_list[0]))
	_output('')
	all_cc = {}
	for location in location_list:
		for cfg_call in cc_by_location.get(location, []):
			all_cc[cfg_call['option']] = cfg_call

	def _sort_by_default_exists(opt):
		return (all_cc[opt].get('default') is not None, all_cc[opt]['option_display'])
	for opt in sorted(all_cc, key=_sort_by_default_exists):
		cfg_call = all_cc[opt]
		for sub_cc in cfg_call.get('prepend_options', []):
			_display_option(sub_cc, user_dict, enum_info_dict)
		_display_option(cfg_call, user_dict, enum_info_dict)
		for sub_cc in cfg_call.get('append_options', []):
			_display_option(sub_cc, user_dict, enum_info_dict)
	_output('')


def _display_location_deep(location, cc_by_location, user_dict, plugin_infos, enum_info_dict):
	bases = [location]
	for base in plugin_infos.get(location, {}).get('bases', []):
		if base not in ['object', 'Plugin', 'ConfigurablePlugin', 'NamedPlugin']:
			bases.append(base)
	_display_location(bases, cc_by_location, user_dict, enum_info_dict)


def _display_option(cfg_call, user_dict, enum_info_dict):
	try:
		opt_line = (cfg_call.get('opt_line', user_dict['format']['output_opt']) % cfg_call).strip()
		while '%(' in opt_line:
			opt_line = opt_line % cfg_call
		for enum, enum_info in enum_info_dict.items():
			if '<enum_values:%s>' % enum in opt_line:
				opt_line = opt_line.replace('<enum_values:%s>' % enum, enum_info['enum_values'])
			if '<enum:%s' % enum in opt_line:
				for enum_value in enum_info['enum_values_raw']:
					opt_line = opt_line.replace('<enum:%s:<attr:%s>>' % (enum, enum_value.lower()), enum_value)
					opt_line = opt_line.replace('<enum:%s:<attr:%s>>' % (enum, enum_value.upper()), enum_value)
		_output('* %s' % opt_line)
		desc = cfg_call.get('desc_line', user_dict['format']['output_desc']) % cfg_call
		desc = (desc % cfg_call).strip()
		if desc:
			for line in desc.split('\n'):
				_output(('    %s' % line).rstrip())
			_output('')
		else:
			if sys.argv[1:] == ['stop']:
				raise Exception(cfg_call['option'] + ' no desc')
			elif sys.argv[1:] == ['count']:
				_output('N/A')
	except Exception:
		_output(json.dumps(cfg_call, indent=2, sort_keys=True))
		raise


def _get_available_plugins(plugin_infos):
	available_plugins = {}
	for plugin in plugin_infos:
		for base in plugin_infos[plugin]['bases']:
			alias_list = plugin_infos[plugin].get('alias', [])
			if alias_list:
				alias_list = lidfilter(alias_list)
				plugin_name = '%s_' % plugin
				if alias_list:
					plugin_name = '%s_ (alias: %s)' % (plugin, str.join(', ', alias_list))
				available_plugins.setdefault(base, []).append(plugin_name)
	return available_plugins


def _get_cc_by_location(user_dict, opt_to_cc_list, used_remap):
	cc_by_location = {}
	for location in user_dict['manual options']:
		for cfg_call in user_dict['manual options'][location]:
			cfg_call.update(user_dict['api'][cfg_call['api']])
			cfg_call['output_altopt'] = ''
			cfg_call['option_display'] = cfg_call['option']
			if cfg_call['default'] is not None:
				cfg_call['output_default'] = user_dict['format']['output_default'] % cfg_call['default']
			cc_by_location.setdefault(location, []).append(cfg_call)

	for opt in opt_to_cc_list:
		for cfg_call in opt_to_cc_list[opt]:
			if not cfg_call.get('disabled'):
				cc_by_location.setdefault(cfg_call['location'], []).append(cfg_call)

	for location in user_dict['location_force']:
		cc_by_location.setdefault(location, [])

	for location in user_dict['location_remap']:
		if location not in used_remap:
			raise Exception('Remap location is unused: %s' % location)

	user_location_list = user_dict['location_whitelist'] + user_dict['location_blacklist']
	for location in user_location_list:
		if location not in cc_by_location:
			raise Exception('User specified location %r does not exist' % location)

	return cc_by_location


def _get_config_default(cfg_call):
	if 'default' in cfg_call['kwargs']:
		return cfg_call['kwargs'].pop('default')
	if cfg_call['args']:
		return cfg_call['args'].pop(0)


def _get_config_option_list(cfg_call):
	arg_options = cfg_call['args'].pop(0)
	if isinstance(arg_options, list):
		option_list = lmap(_make_opt, arg_options)
		option_list.reverse()
		return option_list
	return [_make_opt(arg_options)]


def _get_enum_default(cfg_call):
	default_raw = cfg_call['default_raw'].lower()
	enum_match = _match_enum(default_raw, cfg_call['enum_values_raw'])
	if enum_match is not None:
		return enum_match
	return cfg_call['default_raw']


def _get_enum_info(call_enum_name, call_enum_subset, enum_info_dict):
	for enum, enum_info in enum_info_dict.items():
		if call_enum_name == '<name:%s>' % enum:
			enum_info = dict(enum_info)
			if isinstance(call_enum_subset, list):
				subset_values = lmap(lambda call_enum:
					_match_enum(call_enum, enum_info['enum_values_raw']), call_enum_subset)
				enum_info['enum_values_raw'] = subset_values
				enum_info['enum_values'] = str.join('|', subset_values)
			elif isinstance(call_enum_subset, str):
				subset_values = enum_info['enum_alias'][call_enum_subset]
				enum_info['enum_values_raw'] = subset_values
				enum_info['enum_values'] = str.join('|', subset_values)
			return enum_info


def _get_enum_info_dict(user_dict, enum_value_dict):
	enum_info_dict = {}

	for enum, enum_values_raw in enum_value_dict.items():
		enum_info = enum_info_dict.setdefault(enum, {})
		enum_info['enum'] = enum
		enum_info['enum_desc'] = ''
		enum_info['enum_value_desc'] = {}
		enum_info['enum_values_raw'] = []
		if enum_values_raw != '<manual>':
			enum_info['enum_values_raw'] = lmap(str.upper, enum_values_raw)

	for enum, user_enum_info in user_dict['enums'].items():
		enum_info_dict[enum].update(user_enum_info)

	for enum, enum_info in enum_info_dict.items():
		if not enum_info.get('enum_values'):
			if enum_info['enum_values_raw'] == '<manual>':
				enum_info['enum_values'] = '<manual>'
			else:
				enum_info['enum_values'] = str.join('|', enum_info['enum_values_raw'])

	for enum_value in enum_info['enum_values_raw']:
		enum_info['enum_value_desc'].setdefault(enum_value, '')

	return enum_info_dict


def _get_json(fn):
	try:
		unicode()

		def _remove_unicode(obj):
			if unicode == str:
				return obj
			if isinstance(obj, (list, tuple, set)):
				(obj, old_type) = (list(obj), type(obj))
				for idx, value in enumerate(obj):
					obj[idx] = _remove_unicode(value)
				obj = old_type(obj)
			elif isinstance(obj, dict):
				result = {}
				for key, value in obj.items():
					result[_remove_unicode(key)] = _remove_unicode(value)
				return result
			elif isinstance(obj, unicode):
				return obj.encode('utf-8')
			return obj
	except NameError:
		def _remove_unicode(obj):
			return obj
	fp = open(fn)
	result = json.load(fp)
	fp.close()
	return _remove_unicode(result)


def _get_opt_to_cc_list(config_call_list, available_plugins, enum_info_dict, plugin_infos):
	opt_to_cc_list = {}
	for cfg_call in config_call_list:
		try:
			cfg_fqfn = cfg_call['fqfn']
			if cfg_call['callers'][-1] in ['__init__', '__new__']:
				cfg_call['callers'].pop()
			cfg_call['location'] = str.join('.', cfg_call['callers'])
			cfg_call['bases'] = plugin_infos.get(cfg_call['callers'][0], {}).get('bases', [])
			if cfg_fqfn.startswith('pconfig'):
				_process_pcfg_call(cfg_call, available_plugins, enum_info_dict, plugin_infos)
			else:
				_process_cfg_call(cfg_call, available_plugins, enum_info_dict, plugin_infos)

			# Catch unknown (kw)args
			if cfg_call['args']:
				raise Exception('Unknown args!')
			if cfg_call['kwargs']:
				raise Exception('Unknown kwargs!')

			opt_to_cc_list.setdefault(cfg_call['option'], []).append(cfg_call)
		except Exception:
			_output(json.dumps(cfg_call, indent=2))
			raise
	return opt_to_cc_list


def _get_sub_cc(cfg_call, sub_cc_list):
	result = []
	for sub_cc in sub_cc_list:
		tmp = dict(cfg_call)
		tmp.update(sub_cc)
		result.append(tmp)
	return result


def _make_opt(value):
	tmp = value.lower().replace("'", ' ')
	while '  ' in tmp:
		tmp = tmp.replace('  ', ' ')
	return tmp.strip()


def _match_enum(value, enum_values_raw):
	for enum_value in enum_values_raw:
		if '<attr:%s>' % enum_value.lower() in value.lower():
			return enum_value


def _output(value):
	sys.stdout.write(value + '\n')


def _process_cfg_call(cfg_call, available_plugins, enum_info_dict, plugin_infos):
	process_handler = {
		'get_enum': _process_get_enum,
		'get_lookup': _process_get_lookup,
		'get_time': _process_get_time,
		'get_list': _process_get_list,
		'get_path': _process_get_path_api,
		'get_path_list': _process_get_path_api,
		'get_fn': _process_get_path_api,
		'get_fn_list': _process_get_path_api,
		'get_dn': _process_get_path_api,
		'get_dn_list': _process_get_path_api,
		'get_plugin': _process_get_plugin,
		'get_composited_plugin': _process_get_composited_plugin,
	}

	# cfg_call['id'] = os.urandom(10)
	cfg_call['raw_args'] = list(cfg_call['args'])
	cfg_call['raw_kwargs'] = dict(cfg_call['kwargs'])

	cfg_call['options'] = _get_config_option_list(cfg_call)
	cfg_call['option'] = cfg_call['options'][0].strip()

	# Capture first arg in get_enum - which is not the default but the enum
	if cfg_call['api'] == 'get_enum':
		enum_name = cfg_call['args'].pop(0)
		enum_subset = cfg_call['kwargs'].pop('subset', None)
		cfg_call.update(_get_enum_info(enum_name, enum_subset, enum_info_dict))

	cfg_call['default_raw'] = _get_config_default(cfg_call)
	cfg_call['default'] = cfg_call['default_raw']

	process_fun = process_handler.get(cfg_call['api'])
	if process_fun:
		process_fun(cfg_call)

	if cfg_call['api'] == 'get_filter':
		cfg_call['negate'] = cfg_call['kwargs'].pop('negate', False)
		cfg_call['default_matcher'] = cfg_call['kwargs'].pop('default_matcher', 'start')
		cfg_call['default_order'] = cfg_call['kwargs'].pop('default_order', '<attr:source>')
		for enum in enum_info_dict['ListOrder']:
			cfg_call['default_order'] = cfg_call['default_order'].replace('<attr:%s>' % enum, enum)
		cfg_call['default_filter'] = cfg_call['kwargs'].pop('default_filter', 'strict')

	if cfg_call['api'] == 'get_matcher':
		cfg_call['default_matcher'] = cfg_call['kwargs'].pop('default_matcher', 'start')
		cfg_call['available'] = lfilter(_select_normal_cls_name, available_plugins['Matcher'])

	if cfg_call['api'] in ['get_plugin', 'get_composited_plugin', 'docgen:get_broker']:
		if cfg_call['cls'] not in available_plugins:
			cfg_call['available'] = [cfg_call['cls']]
		else:
			cfg_call['available'] = lfilter(_select_normal_cls_name, available_plugins[cfg_call['cls']])
			cfg_call['available_multi'] = lfilter(_select_multi_cls_name, available_plugins[cfg_call['cls']])
		cfg_call['cls_bases'] = plugin_infos.get(cfg_call['cls'], {}).get('bases', []) + [cfg_call['cls']]

	if cfg_call['api'] == 'get_dict':
		cfg_call['default_order'] = cfg_call['kwargs'].pop('default_order', None)
		if cfg_call['default_order'] is not None:
			cfg_call['default_order'] = lmap(eval, cfg_call['default_order'])
		if cfg_call['default'] is not None:
			default = eval(cfg_call['default'])  # pylint:disable=eval-used
			default_dict = (default, cfg_call['default_order'] or list(default))
			cfg_call['default'] = repr(_str_dict_cfg(default_dict))

	cfg_call['kwargs'].pop('filter_str', None)
	cfg_call['kwargs'].pop('filter_parser', None)
	cfg_call['kwargs'].pop('strfun', None)
	cfg_call['kwargs'].pop('parser', None)
	cfg_call['kwargs'].pop('override', None)
	cfg_call['kwargs'].pop('parse_item', None)
	cfg_call['kwargs'].pop('interactive_msg', None)


def _process_get_composited_plugin(cfg_call):
	_process_get_plugin(cfg_call)
	if 'default_compositor' in cfg_call['kwargs']:
		cfg_call['compositor'] = cfg_call['kwargs'].pop('default_compositor')
	else:
		cfg_call['compositor'] = cfg_call['args'].pop(0)
	if (cfg_call['cls'] == 'Broker') and (cfg_call['api'] == 'get_composited_plugin'):
		cfg_call['api'] = 'docgen:get_broker'
		cfg_call['broker_prefix'] = cfg_call['pargs'][0].strip('"').strip("'")


def _process_get_enum(cfg_call):
	if cfg_call['default_raw'] is not None:
		cfg_call['default'] = _get_enum_default(cfg_call)


def _process_get_list(cfg_call):
	if (cfg_call['default_raw'] is not None) and not isinstance(cfg_call['default_raw'], str):
		cfg_call['default'] = repr(str.join(' ', imap(lambda x: str(x).strip("'"), cfg_call['default'])))


def _process_get_lookup(cfg_call):
	cfg_call['single'] = cfg_call['kwargs'].pop('single', True)
	if cfg_call['default'] == '{}':
		cfg_call['default'] = "''"
	cfg_call['default_matcher'] = cfg_call['kwargs'].pop('default_matcher', "'StartMatcher'")


def _process_get_path_api(cfg_call):
	cfg_call['must_exist'] = cfg_call['kwargs'].pop('must_exist', True)
	if (cfg_call['default_raw'] is not None) and not isinstance(cfg_call['default_raw'], str):
		cfg_call['default'] = repr(str.join(' ', imap(lambda x: str(x).strip("'"), cfg_call['default'])))


def _process_get_plugin(cfg_call):
	cls_name = cfg_call['kwargs'].pop('cls')
	if cls_name.startswith('<name:'):
		cls_name = cls_name[6:-1]
	else:
		cls_name = cls_name.strip("'")
	cfg_call['cls'] = cls_name
	cfg_call['require_plugin'] = cfg_call['kwargs'].pop('require_plugin', True)
	cfg_call['kwargs'].pop('pargs', None)
	cfg_call['kwargs'].pop('pkwargs', None)
	cfg_call['kwargs'].pop('bind_args', None)
	cfg_call['kwargs'].pop('bind_kwargs', None)


def _process_get_time(cfg_call):
	if isinstance(cfg_call['default'], int):
		default_time = cfg_call['default']
		if default_time > 0:
			cfg_call['default'] = _str_time(default_time)


def _process_pcfg_call(cfg_call, available_plugins, enum_info_dict, plugin_infos):
	if cfg_call['api'] in ['get', 'get_bool', 'get_parameter']:
		vn = cfg_call['args'].pop(0).strip("'")
		opt = None
		default = None
		cfg_call['option'] = vn
		if cfg_call['args']:
			opt = cfg_call['args'].pop(0)
			if opt:
				opt = opt.strip("'")
				cfg_call['option'] = ('%s %s' % (vn, opt)).strip()
		if cfg_call['args']:
			default = cfg_call['args'].pop(0)
		elif 'default' in cfg_call['kwargs']:
			default = cfg_call['kwargs'].pop('default')
		cfg_call['default'] = default
		cfg_call['options'] = [cfg_call['option']]
		cfg_call['location'] = cfg_call['location'].replace('.create_psrc', '')
		cfg_call['location'] = cfg_call['location'].replace('.parse_tuples', '')
		cfg_call['location'] = cfg_call['location'].replace('.parse_value', '')


def _rewrite_user_dict(user_dict):
	user_json = json.dumps(user_dict, indent=4, sort_keys=True)
	user_json = user_json.replace(' ' * 4, '\t').replace(' \n', '\n')
	open('docgen_user.json', 'w').write(user_json)


def _select_multi_cls_name(cls_name):
	return ('Multi' in cls_name) and not _select_non_user_cls(cls_name)


def _select_non_user_cls(cls_name):
	return ('Testsuite' in cls_name) or ('Base' in cls_name) or ('Internal' in cls_name)


def _select_normal_cls_name(cls_name):
	return ('Multi' not in cls_name) and not _select_non_user_cls(cls_name)


def _str_dict_cfg(value, parser=identity, strfun=str):
	(srcdict, srckeys) = value
	result = ''
	if srcdict.get(None) is not None:
		result = strfun(srcdict[None])
	key_value_iter = imap(lambda k: '%s => %s' % (k, strfun(srcdict[k])), sorted(srckeys))
	return (result + str.join(' <newline> ', key_value_iter)).strip()


def _str_time(secs):
	return '%02d:%02d:%02d' % (int(secs / 3600), int(secs / 60) % 60, secs % 60)


if __name__ == '__main__':
	main()
