import subprocess
import unittest


class TestFilesStructure(unittest.TestCase):

    def test_have_no_tabs(self):
        try:
            out = subprocess.check_output([
                'git', 'grep', '-n', '-I', '-P', '\t',
                # File imported as-is from mediawiki/core
                '--', ':(exclude)dockerfiles/quibble-coverage/phpunit-example.xml'
            ])
            print(out)
            raise AssertionError('Files have tabulations. Check output.')
        except subprocess.CalledProcessError as e:
            self.assertEquals(1, e.returncode,
                              'when there is no tabs: git grep exit 1')
