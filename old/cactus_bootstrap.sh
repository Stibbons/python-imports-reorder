#!/bin/bash
# Please be aware that this file has two usages:
#  - just setup the local environment by installing required packages. In this case this script
#    is launched as a subshell of bash (in Repo step,...)
#  - provide a virtualenv shell (some buildbot steps use this, developers,...). In this case,
#    this script is sourced.

# you can use variable $PYTHON in order to specify which version of python you want to use
# this will create a different virtualenv

# Changing this version will force to rebuild a virtualenv from scratch
BOOTSTRAP_VERSION=1

# possible environment variables:

#  PYTHON: version of python used: python2.6 or python2.7
#  BUILDBOT: version of buildbot to use: eight or nine

function run_admin()
{
    echo "please type sudo password for missing environment setup (you *need* to be suoder): " $*
    sudo $*
}
function setup_bb_env()
{
    if [[ -z $PYTHON ]]; then
        export PYTHON=python2.6
    fi
    if [[ -z $BUILDBOT ]]; then
        export BUILDBOT=eight
    fi

    if [[ -z $http_proxy ]]; then
        echo "set the http_proxy environment variable"
        exit 254
    fi

    if [[ -z $https_proxy ]]; then
        echo "set the https_proxy environment variable"
        exit 254
    fi

    if [[ ! -f /usr/include/$PYTHON/Python.h ]]; then
        echo "installing $PYTHON from PPA"
        run_admin add-apt-repository ppa:fkrull/deadsnakes || return 1
        run_admin apt-get update || return 1
        run_admin apt-get install $PYTHON $PYTHON-dev || return 1
    fi

    if [[ ! -f /var/lib/apt/lists/ppa.launchpad.net_chris-lea_node.js_ubuntu_dists_precise_main_source_Sources &&
          ! -f /var/lib/apt/lists/ppa.launchpad.net_chris-lea_node.js_ubuntu_dists_raring_main_binary-amd64_Packages &&
          ! -f /var/lib/apt/lists/ppa.launchpad.net_chris-lea_node.js_ubuntu_dists_raring_main_binary-i386_Packages ]]; then
        echo "installing nodejs from PPA"
        run_admin add-apt-repository ppa:chris-lea/node.js
        run_admin apt-get update
        run_admin apt-get install nodejs
    fi

    if [[ ! -f /usr/bin/virtualenv ]]; then
        echo "installing virtualenv"
        run_admin apt-get install python-virtualenv || return 1
    fi
    SANDBOX=$(basename $BASE)_sandbox_${PYTHON}_${BUILDBOT}

    # not sure if this is still needed.
    export format_warnings_path=$BASE/config
    export warning_path=$BASE/config/latests_warnings

    ACTIVATE_BIN=$BASE/$SANDBOX/bin/activate

    if [[ `cat $BASE/$SANDBOX/bootstrap_version` != ${BOOTSTRAP_VERSION} ]]; then
        echo "cactus bootstrap changed! removing previous sandbox"
        rm -rf $BASE/$SANDBOX
    fi

    # create a virtualenv confined python environment, this allows
    # us to know exactly that the same env is used for all buildbot envs.
    # we are now using python 2.7 as the equired python environment
    if [[ ! -d $BASE/$SANDBOX || ! -f $ACTIVATE_BIN ]]; then
        [ -d $BASE/$SANDBOX ] && echo "cleaning dirty sandbox $BASE/$SANDBOX..." && rm -rf $BASE/$SANDBOX
        virtualenv --python=$PYTHON --no-site-packages $BASE/$SANDBOX
        echo $BOOTSTRAP_VERSION > $BASE/$SANDBOX/bootstrap_version
    fi

    # activate the sandbox
    echo "Activating sandbox $ACTIVATE_BIN"
    . $ACTIVATE_BIN
    if [[ -z $ONLY_ACTIVATE_SANDBOX ]]; then

        # make sur the no_proxy variable is set
        # so that we can connect to artifactory directly
        if [[ -z $no_proxy || $(echo $no_proxy | grep -v ".intel.com") == 0 ]]; then
            export no_proxy=localhost,.intel.com
        fi

        # this is our pypi mirror, so that the installation is much faster
        # and not bound to pypi being on-line (it often happens that pypi is down)
        PYPI_URL=http://mcg-depot.intel.com:8081/artifactory/pypi/

        # some packages that we want, and that are not strict dependencies from buildbot
        EXTRA_PACKAGES="Twisted mock sphinx epydoc coverage mysql-python pylint==1.0.0 ipdb pep8 autopep8  logilab-common==0.60.0"
        if [[ $PYTHON == python2.6 ]]; then
            EXTRA_PACKAGES="$EXTRA_PACKAGES argparse"
        fi
        # install dependency of mysql-python if necessary
        if [[ $EXTRA_PACKAGES != *mysql-python* ]]; then
            which mysql_config || run_admin apt-get install libmysqlclient-dev
        fi

        # for each python repository of the manifest, we look for "setup.py"
        # and we will install them in the virtualenv as "editable"
        # this is the equivalent for python setup.py <develop>
        # but pip is looking for the dependencies in our internal mirror
        projects=$(repo forall -g ${BUILDBOT} -c 'echo $PWD')
        for project in $projects ; do
           dirs=$(find $project -name setup.py -execdir pwd \;)
           for d in $dirs; do
             pip install --no-index --find-links $PYPI_URL -e $d || return 1
           done
        done

        # install the extra packages
        echo "Installing extra packages: $EXTRA_PACKAGES"
        eval pip install --no-index --find-links $PYPI_URL $EXTRA_PACKAGES || return 1
    fi
}
