import os
import subprocess

CASTOR_LOAD_SCRIPT = os.path.relpath(os.path.join(
    os.path.dirname(__file__),
    '../jjb/castor-load-sync.bash'))

default_env = {
    'JOB_NAME': 'some-job',
    'CASTOR_NAMESPACE': 'path/to/x/y',
    }


def run_castor_load(env={}):
    script = """
    set -eu -o pipefail
    # Enable alias in non interactive script
    shopt -s expand_aliases
    # Mock
    alias rsync="echo rsync"
    source %s
    """ % CASTOR_LOAD_SCRIPT

    run_env = {}
    run_env.update(default_env)
    run_env.update(env)

    return subprocess.check_output(
        ['bash', '-c', script],
        env=run_env,
        )


def assert_castor_output(expected, env={}):
    actual = run_castor_load(env)
    message = """
    Failure in running castor load
    --- Environment -----
    %s
    --- Expected --------
    %s
    --- Actual ----------
    %s
    ---------------------
    """ % (env, expected, actual)
    assert expected in actual, message


def test_basic_run():
    assert_castor_output(
        'rsync://integration-castor05.integration.eqiad.wmflabs:'
        '/caches/path/to/x/y')


def test_passing_castor_host():
    host = 'castor-service.example.org'
    assert_castor_output(
        'rsync://%s:/caches/path/to/x/y' % host,
        {'CASTOR_HOST': host}
    )
