#!/usr/bin/env python
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

__import__('sys').path.append(__import__('os').path.join(__import__('os').path.dirname(__file__), '..'))
__import__('testfwk').setup(__file__)
# - prolog marker
import shutil
from testfwk import run_test, testfwk_create_workflow
from grid_control_gui.plugin_graph import get_workflow_graph


config_dict = {
	'global': {'task': 'UserTask', 'backend': 'Host'},
	'jobs': {'nseeds': 1},
	'task': {'wall time': '1', 'executable': 'create_graph.py', 'dataset': '../datasets/dataA.dbs', 'files per job': 1},
}

workflow = testfwk_create_workflow(config_dict)
del workflow.testsuite_config

open('devtool.dot', 'w').write(get_workflow_graph(workflow))
shutil.rmtree('work')

run_test()
