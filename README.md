# Wikimedia configuration for Jenkins

This repository holds the configuration of the Wikimedia Foundation Inc. Jenkins
jobs. It is meant to be used with a python script written by the OpenStack
Foundation: Jenkins Job Builder.

When you tweak or add jobs, follow the documentation maintained on mediawiki.org:

  https://www.mediawiki.org/wiki/CI/JJB

For more about the Jenkins Job Builder software and how to use it, refer to the upstream documentation:

  https://docs.openstack.org/infra/jenkins-job-builder/

## Example Usage

Make sure you have tox and python 3 installed, you can then run Jenkins job builder using:

    $ ./jenkin-jobs <arguments>

Generate XML files for Jenkins jobs from YAML files:

    $ ./jenkins-jobs test ./jjb/ --config-xml -o output/

Update Jenkins jobs which name starts with "selenium":

    $ ./jenkins-jobs --conf jenkins_jobs.ini update ./jjb/ selenium*

There are a few wrappers provided to easily test, update or delete jobs:

Delete the job `build-project` or jobs matching fnmatch `*node6*`:

    $ ./jjb-delete build-project
    $ ./jjb-delete '*node6*'

Generate a given job and print the generated XML:

   $ ./jjb-test 'wip-job'

Delete one or more jobs:

   $ ./jjb-delete 'obsolete-job'
   $ ./jjb-delete '*php5*'

## Running tests

To test the configuration, we use tox and you need at least version 1.9+ ([bug T125705](https://phabricator.wikimedia.org/T125705))
to run the test suite. Running `tox` in the main dir of your local clone runs the tests.

## Add volunteer users to the allow list

See https://www.mediawiki.org/wiki/Continuous_integration/Allow_list

# Deployments

Use the `./fab` helper for deployment actions:

    $ ./fab deploy_zuul
    $ ./fab deploy_docker
    $ ./fab docker_pull_image <imagename>
