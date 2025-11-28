# Wikimedia configuration for Jenkins

This repository holds the configuration of the Wikimedia Foundation Inc. Jenkins
jobs. It is meant to be used with a python script written by the OpenStack
Foundation: Jenkins Job Builder.

When you tweak or add jobs, follow the documentation maintained on mediawiki.org:
https://www.mediawiki.org/wiki/CI/JJB

For more about the Jenkins Job Builder software and how to use it, refer to the upstream documentation:
https://docs.openstack.org/infra/jenkins-job-builder/

## Directories

* dockerfiles - Definition of CI images using https://doc.wikimedia.org/docker-pkg/
* jjb - JJB stands for Jenkins Job Builder. It is a python script to maintain and simplify configuration of Jenkins jobs. https://www.mediawiki.org/wiki/Continuous_integration/Jenkins_job_builder
* tests - Hosts test suite for the CI configuration
* utils - Miscellaneous scripts to support CI configuration
* zuul - Configuration for Zuul, the workflow and scheduler https://www.mediawiki.org/wiki/Zuul

## Jenkins job local testing and deployment

First create a jenkins_jobs.ini file e.g.

    [job_builder]
    allow_duplicates=True

    [jenkins]
    user=USERNAME
    password=API_TOKEN
    url=https://integration.wikimedia.org/ci/
    query_plugins_info=False

Make sure you have tox and python 3 installed, you can then run Jenkins job builder using:

    $ ./jenkins-jobs <arguments>

Generate from the YAML an XML file for each Jenkins job, in the `output/` directory:

    $ ./jenkins-jobs test ./jjb/ --config-xml -o output/

Generate from the YAML an XML file for a single Jenkins job, and output it to stdout:

    $ ./jjb-test 'wip-job'

Once happy with your changes to the Jenkins Job Builder definition, commit them
and review the difference:

    $ ./utils/jjb-diff.sh

A CHANGELOG output will be emitted which you can copy paste to the commit
message (`git commit --amend`).

Update in production CI a single Jenkins job:

    $ ./jenkins-jobs --conf jenkins_jobs.ini update ./jjb/ 'updated-job'
    (or)
    $ ./jjb-update 'updated-job'

    Note: push JJB updates to CI and verify them *before* merging the patch.

Update in production CI all Jenkins jobs matching a filter:

    $ ./jenkins-jobs --conf jenkins_jobs.ini update ./jjb/ 'updated-jobs*'
    (or)
    $ ./jjb-update 'updated-jobs*'

    Note: push JJB updates to CI and verify them *before* merging the patch.

Delete from production CI a single Jenkins job:

    $ ./jenkins-jobs --conf jenkins_jobs.ini delete ./jjb/ 'obsolete-job'
    (or)
    $ ./jjb-delete 'obsolete-job'

# Zuul configuration

## Running tests locally

To test the configuration, we use tox and you need at least version 1.9+ ([bug T125705](https://phabricator.wikimedia.org/T125705))
to run the test suite. Running `tox` in the main dir of your local clone runs the tests.

## Add volunteer users to the allow list

See https://www.mediawiki.org/wiki/Continuous_integration/Allow_list

## Deployment

Once the change is merged, use the `./fab` helper to deploy your CI config change to production CI:

    $ ./fab deploy_zuul

# Docker image buiding and publishing

After making the relevant `Dockerfile.template` changes and adding the changelog entry, you can
locally build and test the new version of the image by running:

    $ docker-pkg -c dockerfiles/config.yaml build --select '*/my-image:*' dockerfiles/

Where "my-image" is the name of the docker image. This will try to pull any parent images from the registry if missing locally, and will build them as-needed if not found.

Or, to fetch or build all images:

    $ docker-pkg -c dockerfiles/config.yaml --info build dockerfiles/

Once the image is built, you can use the debug-image tool to test it interactively:

    $ ./dockerfiles/debug-image my-image/

(If you cd into dockerfiles you can tab-complete on the name of docker images.)

If you are changing an image that is used by other images, you must cascade your changes so that you are the one to deal with issues, not a later user. Run:

    $ docker-pkg -c dockerfiles/config.yaml --info update --reason "Reason to make this change" --version 1.2.3 updated-root-image dockerfiles/

Once the change is merged, use the `./fab` helper to build and publish your image to Wikimedia's docker registry:

    $ ./fab deploy_docker

In rare cases, you may need:

    $ ./fab docker_pull_image <imagename>

To spot where the JJB definitions are using outdated docker images, use:

    $ ./utils/docker-updates
    <list of updates>
    Apply updates? [y/N]: y

It will shows a list of images to update and prompts for confirmation. The prompt can be automatically accepted by using `--apply`:

    $ ./utils/docker-updates --apply
    <list of updates>
    Applying changes ...
    Updated jjb/integration.yaml
    Updated jjb/mediawiki.yaml

The changes to the jobs can then be reviewed with `./utils/jjb-diff.sh`.
