TOOLDIR="$(dirname $0)"
cd "$TOOLDIR"
TOOLDIR="$(pwd -P)"
BASEDIR="$TOOLDIR/../.."
export PYTHONPATH="$BASEDIR/packages:$PYTHONPATH"

echo "fixing version"
echo "-----------------------------"
python $TOOLDIR/update_version.py

echo "fixing imports"
echo "-----------------------------"

python $TOOLDIR/imports_all.py
python $TOOLDIR/imports_check.py
python $TOOLDIR/imports_sort.py

echo "============================="
echo "fixing compat imports"
echo "-----------------------------"

cd "$BASEDIR"
python packages/python_compat.py 2>&1 | grep -v requests | grep -v xmpp
cd - > /dev/null

echo "============================="
echo "updating plugins"
echo "-----------------------------"

cd "$BASEDIR/packages"
python grid_control_update.py
cd - > /dev/null

echo "============================="
echo "sorting files"
echo "-----------------------------"

cd "$BASEDIR"
ALL_FILES="\
	packages/grid_control/backends/*.py \
	packages/grid_control/backends/condor_wms/*.py \
	packages/grid_control/config/*.py \
	packages/grid_control/datasets/*.py \
	packages/grid_control/parameters/*.py \
	packages/grid_control/tasks/*.py \
	packages/grid_control/utils/*.py \
	packages/grid_control_cms/*.py \
	packages/grid_control_gui/*.py \
	packages/grid_control_usb/*.py \
	packages/grid_control_tests/*.py \
	packages/hpfwk/*.py \
	scripts/*.py
	setup.py
	go.py
"
FILTER_FILES=$(ls $ALL_FILES | grep -v Lexicon.py | grep -v cmsoverlay.py | grep -v lumiInfo.py | grep -v downloadFromSE.py)
python "$TOOLDIR/devtool_sort_code.py" $FILTER_FILES 2>&1 | grep -v WARNING
cd - > /dev/null

echo "============================="
echo "updating headers"
echo "-----------------------------"

python "$TOOLDIR/header_copyright.py" | grep changed

echo "============================="
echo "updating notice"
echo "-----------------------------"

python "$TOOLDIR/commit_stats.py"

echo "============================="
echo "updating documentation"
echo "-----------------------------"

python docgen_parse_code.py
python docgen_plugin_infos.py | sort | uniq > /dev/null
python docgen.py stop > "$BASEDIR/docs/config.rst"
