#!/usr/bin/env python3
"""Find Jenkins jobs defined in jjb/ that aren't referenced in zuul/layout.yaml."""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import yaml

BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
LAYOUT_YAML = os.path.join(BASE_DIR, 'zuul', 'layout.yaml')
JJB_DIR = os.path.join(BASE_DIR, 'jjb')
JENKINS_JOBS = os.path.join(BASE_DIR, 'jenkins-jobs')
JENKINS_JOBS_INI = os.path.join(BASE_DIR, 'jenkins_jobs.ini')

# Jobs that exist in Zuul but are not Jenkins jobs
ZUUL_INTERNAL_JOBS = {'noop'}


# Triggers from outside of Zuul that we should ignore
CRON_TRIGGER_TAGS = {
    'hudson.triggers.SCMTrigger',   # pollscm:
    'hudson.triggers.TimerTrigger',  # timed:
}

# Jenkins XML elements that indicate a job launches another job, mapped to the
# child element that holds the (comma-separated) target job name(s).
JENKINS_TRIGGER_ELEMENTS = {
    # trigger-builds builder / publisher (Parameterized Trigger plugin)
    'hudson.plugins.parameterizedtrigger.TriggerBuilder': 'projects',
    'hudson.plugins.parameterizedtrigger.BuildTrigger': 'projects',
    # trigger publisher (built-in "Build other projects")
    'hudson.tasks.BuildTrigger': 'childProjects',
}


def has_cron_trigger(xml_path):
    """Return True if the job XML contains a SCM poll or timer trigger."""
    tree = ET.parse(xml_path)
    triggers = tree.getroot().find('triggers')
    if triggers is None:
        return False
    return any(child.tag in CRON_TRIGGER_TAGS for child in triggers)


def get_jenkins_triggered_jobs(tmpdir):
    """Return set of job names that are triggered by other Jenkins jobs.

    Scans all job XMLs for parameterized trigger plugin entries and collects
    the names of any jobs they reference as downstream targets.
    """
    triggered = set()
    for name in os.listdir(tmpdir):
        tree = ET.parse(os.path.join(tmpdir, name))
        root = tree.getroot()
        for section in (root.find('builders'), root.find('publishers')):
            if section is None:
                continue
            for element in section:
                child_tag = JENKINS_TRIGGER_ELEMENTS.get(element.tag)
                if child_tag is None:
                    continue
                for child_el in element.iter(child_tag):
                    for proj in child_el.text.split(','):
                        triggered.add(proj.strip())
    return triggered


def get_jjb_jobs():
    """Return set of job names defined in jjb/ by running jenkins-jobs test.

    Jobs with a cron-based trigger (pollscm or timed) are excluded, as they
    run independently of Zuul and don't need a zuul/layout.yaml reference.
    Jobs triggered by other Jenkins jobs are also excluded, as they don't need
    a direct Zuul reference (e.g. alerts-pipeline-test triggered by
    trigger-alerts-pipeline-test, or beta-scap-sync-world triggered by
    beta-code-update-eqiad).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            subprocess.run(
                [JENKINS_JOBS, '--conf', JENKINS_JOBS_INI,
                 'test', JJB_DIR, '-o', tmpdir],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            print('jenkins-jobs test failed: %s' % e, file=sys.stderr)
            sys.exit(1)
        triggered_jobs = get_jenkins_triggered_jobs(tmpdir)
        return {
            name for name in os.listdir(tmpdir)
            if not has_cron_trigger(os.path.join(tmpdir, name))
            and name not in triggered_jobs
        }


def get_zuul_jobs():
    """Return set of job names referenced in zuul/layout.yaml."""
    with open(LAYOUT_YAML) as f:
        layout = yaml.safe_load(f)

    jobs = set()

    def collect_from_section(section):
        for entry in section:
            for key, val in entry.items():
                if key in ('name', 'template'):
                    continue
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, str):
                            jobs.add(item)
                        elif isinstance(item, dict) and 'name' in item:
                            jobs.add(item['name'])

    collect_from_section(layout.get('project-templates', []))
    collect_from_section(layout.get('projects', []))

    jobs -= ZUUL_INTERNAL_JOBS
    return jobs


def main():
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        print('usage: jjb-zuul-unused')
        sys.exit(0)

    jjb_jobs = get_jjb_jobs()
    zuul_jobs = get_zuul_jobs()

    unused = sorted(jjb_jobs - zuul_jobs)

    if not unused:
        print('All JJB jobs are referenced in zuul/layout.yaml')
        sys.exit(0)

    for job in unused:
        print(job)


if __name__ == '__main__':
    main()
