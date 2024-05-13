# Generate Jenkins jobs

import argparse
from glob import glob
import logging
import os
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from jenkins_jobs.cli.entry import JenkinsJobs
from nose.plugins.attrib import attr
import zuul.cmd.server

JENKINS_ACCEPTABLE_LABELS = [
    'BetaClusterBastion',  # deployment-prep
    'blubber',  # dummy job for Zuul/Gearman which trigger a pipeline job
    'castor',  # Central cache
    'contint1002',  # Publishing
    'puppet',
    'puppet5-compiler-node',
    'puppet7-compiler-node',
    'train',
    'trigger',
    # The Docker agents:
    'Docker',
]


class IntegrationTests(unittest.TestCase):

    jjb_out_dir = None

    @classmethod
    def setUpClass(cls):
        cls.jjb_out_dir = tempfile.mkdtemp()
        cls.generate_jjb_jobs(cls.jjb_out_dir)

    @classmethod
    def tearDownClass(cls):
        if cls.jjb_out_dir:
            shutil.rmtree(cls.jjb_out_dir)

    @staticmethod
    def generate_jjb_jobs(out_dir):
        jjb_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '../jjb')
        jjb_test = JenkinsJobs(args=[
            'test', jjb_dir, '--config-xml', '-o', out_dir])
        # Fake the list of plugins to skip retrieval
        jjb_test.jjb_config.builder['plugins_info'] = []
        jjb_test.execute()

    # Merely to show that the config has been generated in setUpClass
    def test_jjb_generate_jobs(self):
        self.assertNotEqual(
            [], os.listdir(self.jjb_out_dir),
            'jjb must have generated jobs')

    def test_jenkins_jobs_have_a_timeout(self):
        lack_timeout = []
        for job_file in glob(self.jjb_out_dir + '/*/config.xml'):

            # Can not handle pipeline jobs
            # They should wrap using timeout(X) {}
            root = ET.parse(job_file).getroot()
            if root.tag in ['flow-definition', 'hudson.model.ListView']:
                continue

            with open(job_file) as f:
                if 'BuildTimeoutWrapper' not in f.read():
                    job_name = os.path.basename(
                        os.path.dirname(f.name))
                    lack_timeout.append(job_name)

        self.maxDiff = None
        self.longMessage = True
        self.assertEquals(
            [], lack_timeout,
            'All Jenkins jobs must have a timeout')

    @attr('qa')
    def test_jenkins_jobs_assigned_nodes(self):
        legacy_node = {}
        for job_file in sorted(glob(self.jjb_out_dir + '/*/config.xml')):
            root = ET.parse(job_file).getroot()

            # Can not handle pipeline jobs
            if root.tag == 'flow-definition':
                continue

            # FIXME handle matrix-project
            if root.tag == 'matrix-project':
                continue

            assignedNode = root.find('./assignedNode').text
            if assignedNode not in JENKINS_ACCEPTABLE_LABELS:
                job_name = os.path.basename(
                    os.path.dirname(job_file))
                legacy_node[os.path.dirname(job_name)] = assignedNode

        self.maxDiff = None
        self.longMessage = True
        self.assertEquals(
            {}, legacy_node,
            'All Jenkins jobs use DebianJessie label')

    def test_jjb_zuul_jobs(self):
        'Zuul jobs are defined by JJB'

        jjb_jobs_file = tempfile.NamedTemporaryFile()
        jjb_jobs_file.write(
            "\n".join(os.listdir(self.jjb_out_dir)))
        jjb_jobs_file.flush()

        this_dir = os.path.dirname(os.path.abspath(__file__))

        zuul_server = zuul.cmd.server.Server()
        zuul_server.args = argparse.Namespace(
            config=os.path.join(this_dir, 'fixtures/zuul-dummy.conf'),
            validate=jjb_jobs_file.name,
        )
        zuul_server.read_config()

        # Mute almost all output from zuul, nosetest should reset the log level
        # after the test has completed.
        logging.getLogger().setLevel(logging.WARNING)

        zuul_server.config.set(
            'zuul', 'layout_config',
            os.path.join(this_dir, '../zuul/layout.yaml'))

        self.assertFalse(zuul_server.test_config(jjb_jobs_file.name))
