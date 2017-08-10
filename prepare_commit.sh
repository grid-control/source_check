TOOLDIR="$(dirname $0)"
cd "$TOOLDIR"
TOOLDIR="$(pwd -P)"
BASEDIR="$TOOLDIR/../.."
export PYTHONPATH="$BASEDIR/packages:$PYTHONPATH"
PYTHONEXEC=python

echo "============================="
echo "self check"
echo "-----------------------------"
TOOLS="$(ls *.py | grep -v create_graph.py)"
$PYTHONEXEC "$TOOLDIR/imports_all.py" $TOOLS
$PYTHONEXEC "$TOOLDIR/imports_check.py" $TOOLS
$PYTHONEXEC "$TOOLDIR/imports_sort.py" $TOOLS
$PYTHONEXEC "$TOOLDIR/check_fun_name.py" $TOOLS
$PYTHONEXEC "$TOOLDIR/devtool_sort_code.py" $TOOLS 2>&1 | grep -v WARNING
$PYTHONEXEC "$TOOLDIR/header_copyright.py" $TOOLS 2>&1 | grep changed

echo "============================="
echo "fixing version"
echo "-----------------------------"
$PYTHONEXEC "$TOOLDIR/update_version.py"

echo "============================="
echo "fixing imports"
echo "-----------------------------"

$PYTHONEXEC "$TOOLDIR/imports_all.py"
$PYTHONEXEC "$TOOLDIR/imports_check.py"
$PYTHONEXEC "$TOOLDIR/imports_sort.py"

echo "============================="
echo "checking names"
echo "-----------------------------"

$PYTHONEXEC "$TOOLDIR/check_fun_name.py"

echo "============================="
echo "fixing compat imports"
echo "-----------------------------"

cd "$BASEDIR"
$PYTHONEXEC "packages/python_compat.py" 2>&1 | grep -v requests | grep -v xmpp
cd - > /dev/null

echo "============================="
echo "updating plugins"
echo "-----------------------------"

cd "$BASEDIR/packages"
$PYTHONEXEC "grid_control_update.py"
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
	packages/hpfwk/*.py \
	scripts/*.py
	setup.py
	go.py
"
FILTER_FILES=$(ls $ALL_FILES | grep -v Lexicon.py | grep -v cmsoverlay.py | grep -v lumiInfo.py | grep -v downloadFromSE.py)
$PYTHONEXEC "$TOOLDIR/devtool_sort_code.py" $FILTER_FILES 2>&1 | grep -v WARNING
cd - > /dev/null

echo "============================="
echo "updating headers"
echo "-----------------------------"

$PYTHONEXEC "$TOOLDIR/header_copyright.py" | grep changed

echo "============================="
echo "updating notice"
echo "-----------------------------"

$PYTHONEXEC "$TOOLDIR/commit_stats.py"

echo "============================="
echo "updating documentation"
echo "-----------------------------"

$PYTHONEXEC "docgen_parse_code.py"
$PYTHONEXEC "docgen_plugin_infos.py" | sort | uniq > /dev/null
$PYTHONEXEC "docgen.py" stop > "$BASEDIR/docs/config.rst"
