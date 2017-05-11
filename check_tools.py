import os, sys


def set_path():
	base_dir = os.path.abspath(os.path.dirname(__file__))
	while 'go.py' not in os.listdir(base_dir):
		base_dir = os.path.normpath(os.path.join(base_dir, '..'))
	sys.path.append(os.path.join(base_dir, 'packages'))
set_path()
