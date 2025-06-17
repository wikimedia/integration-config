#!/usr/bin/env python3

# Reads XML output from JJB and writes all the
# shell commands included to numbered files, allowing
# a linter such as shellcheck to validate them.

from argparse import ArgumentParser
import os
from xml.etree import ElementTree


def extract_shell_scripts(input_file):
    output_dir = os.path.dirname(input_file)
    try:
        tree = ElementTree.parse(input_file)
    except ElementTree.ParseError:
        raise ValueError('Invalid XML file: ' + input_file)
    tasks = tree.getroot().findall('.//hudson.tasks.Shell')
    for i, task in enumerate(tasks):
        script = task.find('command').text
        with open(os.path.join(output_dir, str(i) + '.sh'), 'wt') as f:
            if not script.startswith('#!/'):
                f.write("#!/usr/bin/env bash\n")
            f.write(script)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('input', nargs='+')
    args = parser.parse_args()
    for input_file in args.input:
        extract_shell_scripts(input_file)
