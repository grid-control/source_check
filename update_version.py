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

import os, logging
from grid_control.utils.file_tools import SafeFile


def main():
	os.chdir(os.path.join(os.path.dirname(__file__), '../..'))
	os.system('git rev-parse --short HEAD > .git_version')
	os.system('git log | grep git-svn > .svn_version')
	for line in SafeFile('.svn_version').iter_close():
		svn_version = int(line.split('@')[1].split()[0])
		break
	git_version = SafeFile('.git_version').read_close().strip()
	svn_version += 1
	logging.critical('%s %s', svn_version, git_version)
	os.unlink('.svn_version')
	os.unlink('.git_version')
	fn = 'packages/grid_control/__init__.py'
	line_list = SafeFile(fn).read().splitlines()
	fp = SafeFile(fn, 'w')
	for line in line_list:
		if line.startswith('__version__'):
			version_tuple = (svn_version / 1000, (svn_version / 100) % 10, svn_version % 100, git_version)
			line = "__version__ = '%d.%d.%d (%s)'" % version_tuple
		fp.write(line + '\n')
	fp.close()


if __name__ == '__main__':
	main()
