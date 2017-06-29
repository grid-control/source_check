import os, sys, json, logging
from python_compat import lmap


def main():
	if sys.argv[1:]:
		base_dir = sys.argv[1]
	else:
		base_dir = '../../packages'
	sys.path.append(base_dir)
	from hpfwk.hpf_plugin import get_plugin_list, import_modules

	clsdata = {}
	for package in os.listdir(base_dir):
		package = os.path.abspath(os.path.join(base_dir, package))
		if os.path.isdir(package):
			plugin_list = get_plugin_list(import_modules(os.path.abspath(package), _select))
			for cls in sorted(plugin_list, key=lambda c: c.__name__):
				cls_name = cls.__name__.split('.')[-1]
				clsdata.setdefault(cls_name, {})['alias'] = cls.get_class_name_list()[1:]
				if not clsdata.setdefault(cls_name, {})['alias']:
					logging.warning('%r', cls)
				if cls.config_section_list:
					clsdata.setdefault(cls_name, {})['config'] = cls.config_section_list
					clsdata.setdefault(cls_name, {}).setdefault('scope', {})['config'] = cls.config_section_list

				bases = lmap(lambda x: x.__name__, cls.iter_class_bases())[1:] + ['object']
				bases.reverse()
				if bases:
					clsdata.setdefault(cls_name, {})['bases'] = bases
				else:
					logging.error('%r %r', clsdata, bases)
					sys.exit(0)

	fp = open('docgen_plugin_infos.json', 'w')
	json.dump(clsdata, fp, indent=2)
	fp.close()


def _select(path):
	for pat in ['/share', '_compat_', '/requests', '/xmpp']:
		if pat in path:
			return False
	return True


if __name__ == '__main__':
	main()
