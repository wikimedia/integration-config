#!/usr/bin/python3

# port of https://gitlab.wikimedia.org/repos/test-platform/catalyst/function-orchestrator/-/
# blob/main/catalyst_client/deploy_env.py

import functools
import json
import logging
import os
import random
import subprocess
import sys
import time

import requests

WIKILAMBDA_REF = os.getenv('WIKILAMBDA_REF')
ENV_API_PATH = os.getenv('ENV_API_PATH')
ENV_NAME = "mw-ext-wl-ci-{}-{}".format(os.getenv('ZUUL_CHANGE'), random.randrange(10000, 99999))
ENV_URL = "{}.catalyst.wmcloud.org".format(ENV_NAME)

session = requests.Session()
session.headers.update({
    'Authorization': "ApiToken {}".format(os.getenv('CATALYST_API_TOKEN'))
})
session.request = functools.partial(session.request, allow_redirects=True)

logger = logging.getLogger()


def rest(url, method='get', **kwargs):
    r = getattr(session, method)(url, timeout=120, **kwargs)
    r.raise_for_status()
    return r


def setup_logger():
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    # Prevent printing WARNING, ERROR and CRITICAL
    stdout_handler.addFilter(
        lambda record: record.levelno not in [logging.WARNING, logging.ERROR, logging.CRITICAL]
    )

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)

    formatter = logging.Formatter('%(levelname)s: %(message)s')
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)

    logger.setLevel(logging.INFO)
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)


def create_env():
    try:
        return rest(ENV_API_PATH, 'post', json={
            'name': ENV_NAME,
            'chartName': 'wikifunctions',
            'values': {
                'mediawikiUrl': ENV_URL,
                'wikilambdaRef': ("refs/changes/{}".format(WIKILAMBDA_REF)
                                  if WIKILAMBDA_REF != "" else ""),
                'reposCache': {
                    'use': 'true',
                    'wikiRepos': '/mnt/k3s-data/wiki-repos',
                },
            }
        }).json()
    except Exception as e:
        logger.error("Failed to create Wikifunctions environment: %s", e)
        sys.exit(1)


def stream_creation_logs(env):
    try:
        res = (rest("{}/{}/logs?stream=wikifunctions/install-mediawiki"
               .format(ENV_API_PATH, env['id']), stream=True))
        for log_event in res.iter_lines():
            event_str = log_event.decode('utf-8')
            if event_str.startswith('data:'):
                event_json = json.loads(event_str.removeprefix('data:'))
                log = event_json['logs'][0]
                logger.info("{}: {}".format(log['timestamp'], log['log']))
        return
    except Exception as e:
        if not isinstance(e, requests.HTTPError):
            logger.error("Error while retrieving logs: %s", e)
    logger.error('Environment logs are still not ready. Failing')
    sys.exit(1)


def check_status(env):
    for wait in [5] * 6:
        time.sleep(wait)
        try:
            res = rest("{}/{}".format(ENV_API_PATH, env['id'])).json()
            if res['status'] == 'running':
                (logger.info("Environment is ready and reachable at https://{}. Enjoy!"
                 .format(ENV_URL)))
                return
        except Exception as e:
            logger.error("Error while checking environment creation status: %s", e)
    env_status = res['status'] if res is not None else 'unknown'
    logger.error("Environment is still not ready. Last seen status is '{}'".format(env_status))
    sys.exit(1)


def save_id(env):
    with open("/log/envid", "w") as f:
        f.write("export ENV_ID={}".format(env['id']))


if __name__ == '__main__':
    setup_logger()

    env = create_env()
    save_id(env)
    logger.info("Environment creation started. Streaming logs a soon as they are available")
    stream_creation_logs(env)
    logger.info("Creation logs completed. Will check for environment availability now")
    check_status(env)
    os.environ['MW_SERVER'] = ENV_URL
    subprocess.run(['/run-with-xvfb.sh {}'.format(os.getenv('NPM_ARGS'))], shell=True, check=True)
