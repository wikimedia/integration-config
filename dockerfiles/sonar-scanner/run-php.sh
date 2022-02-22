#!/bin/bash

set -eu
set -o pipefail

umask 002

set +x

PROJECT_NAME=$(basename "$ZUUL_PROJECT")
if [[ $PROJECT_NAME == "core" ]]; then
    cd /workspace/src
else
    cd /workspace/src/extensions/"$PROJECT_NAME"
fi
AUTOGENERATED_PROPERTIES=false

if [[ ! -f sonar-project.properties ]]; then
    AUTOGENERATED_PROPERTIES=true
    # Create directories if they don't already exist, so that sonar-scanner doesn't throw an error
    mkdir -p resources includes languages src modules maintenance tests
    {
        echo "sonar.sources=resources,languages,includes,src,modules,maintenance"
        echo "sonar.exclusions=extensions/**/*,mw-config/**/*,node_modules/**/*,vendor/**/*,skins/**/*,logs/**/*,cache/**/*,resources/lib/**/*"
        echo "sonar.tests=tests"
    } > sonar-project.properties
fi

# If test coverage exists, add this to the properties file.
if [[ -f coverage/lcov.info ]]; then
    echo "sonar.javascript.lcov.reportPaths=coverage/lcov.info" >> sonar-project.properties
fi
if [[ -f /workspace/log/junit.xml ]] && [[ -f /workspace/log/clover.xml ]]; then
    echo "sonar.php.tests.reportPath=/workspace/log/junit.xml" >> sonar-project.properties
    echo "sonar.php.coverage.reportPaths=/workspace/log/clover.xml" >> sonar-project.properties
fi

# Output sonar-project file to assist with debugging:
echo "== sonar-project.properties =="
cat sonar-project.properties

# Initialize analysis, send data to SonarQube
/opt/sonar-scanner/bin/sonar-scanner -Dsonar.login="$SONAR_API_KEY" "$@"

if [[ ${AUTOGENERATED_PROPERTIES} = true ]]; then
    rm sonar-project.properties
fi

# Analysis is sent via a webhook from SonarQube to a web application (SonarQube Bot)
# and the bot will comment in gerrit with Verified +1 for success or comment only
# for failure.
