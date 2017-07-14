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
