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

import os, math, logging, get_file_list
from python_compat import imap, sorted


def main():
	(changes_a_dict, email_dict) = parse_info()

	def _sort_by(author):
		# sort_by_added
		# return (-changes_a_dict[author][0], author.split()[-1])
		# sort_by_removed
		# return (-changes_a_dict[author][1], author.split()[-1])
		# sort_by_changes
		# return (-(changes_a_dict[author][0] + changes_a_dict[author][1]), author.split()[-1])
		# sort_by_contribution
		return (-(changes_a_dict[author][0] - 0.5 * changes_a_dict[author][1]), author.split()[-1])

	fp_r = open('docs/NOTICE')
	fp_w = open('docs/NOTICE.new', 'w')
	wrote_hiscore = False
	for line in fp_r:
		if not line.startswith(' ' * 15):
			fp_w.write(line)
		elif not wrote_hiscore:
			for hs_line in write_hiscore(fp_w, changes_a_dict, email_dict, _sort_by):
				if 'Fred Stober' not in hs_line:
					fp_w.write(hs_line.encode('utf-8'))
			wrote_hiscore = True
	os.rename('docs/NOTICE.new', 'docs/NOTICE')


def parse_info():
	os.chdir(os.path.join(os.path.dirname(__file__), '../..'))
	os.system('git log --pretty="%H|%aN|%aE" --no-merges -w --numstat > commit.log')
	email_dict = {}
	commits_dict = {}
	changes_a_dict = {}
	changes_fn_dict = {}
	for line in imap(str.strip, open('commit.log')):
		if ('|' in line) and ('@' in line):
			author, email = line.split('|')[1:]
			email_dict[author] = email
			commits_dict[author] = commits_dict.get(author, 0) + 1
		elif line:
			add_line, rm_line, fn = line.split(None, 2)
			if add_line == '-':
				continue
			if get_file_list.match_file(fn, show_external=False, no_links=False):
				prev_a = changes_a_dict.get(author, (0, 0))
				changes_a_dict[author] = (prev_a[0] + int(add_line), prev_a[1] + int(rm_line))
				prev_fn = changes_fn_dict.get(fn, (0, 0))
				changes_fn_dict[fn] = (prev_fn[0] + int(add_line), prev_fn[1] + int(rm_line))
	email_dict['Manuel Zeise'] = 'manuel.zeise@sap.com'
	email_dict['Fred Stober'] = 'mail@fredstober.de'
	return (changes_a_dict, email_dict)


def write_hiscore(stream, changes_a_dict, email_dict, sort_fun):
	for author in sorted(changes_a_dict, key=sort_fun):
		log_msg = '(%6d:%6d) ' % changes_a_dict[author]
		log_msg += '%7.1f ' % (-sort_fun(author)[0])
		word_cloud_weight = int(1 + 1 * math.log(1 - sort_fun(author)[0]))
		log_msg += '%s:%s' % (author.replace(' ', ''), word_cloud_weight)
		logging.warning(log_msg)
		notice_msg = ' ' * 15 + '%-23s <%s>\n' % (author.decode('utf-8'), email_dict[author].lower())
		yield notice_msg
	yield '\n'
	yield ' ' * 15 + '(in order of development activity - excluding libraries)'


if __name__ == '__main__':
	main()
