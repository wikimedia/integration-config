@Library('wikimedia-integration-pipelinelib') import org.wikimedia.integration.*

import groovy.json.JsonSlurperClassic

@NonCPS
def parseJson(jsonString) {
  def jsonSlurper = new JsonSlurperClassic()

  jsonSlurper.parseText(jsonString)
}

def globalAllowedCredentials = parseJson('''{{ globalAllowedCredentials | default({}) | tojson }}''')
def pipelineAllowedCredentials = parseJson('''{{ allowedCredentials | default({}) | tojson }}''')

def allowedCredentials = globalAllowedCredentials + pipelineAllowedCredentials

// Restrict use of certain pipeline stage actions for builds coming from Zuul
// pipelines that don't require +2 voting or tag/branch creation in Gerrit.
// Note that builds triggered by processes/people other than Zuul are allowed
// to use all actions as build invocation is already restricted by Jenkins.
def allowedActions = ["build", "copy", "exports", "notify", "run"]

if (params.ZUUL_PIPELINE =~ /^(gate-and-submit.*|postmerge|post|publish)$/) {
  allowedActions += ["deploy", "promote", "publish", "trigger"]
}

def builder = new PipelineBuilder(
  [allowedCredentials: allowedCredentials],
  ".pipeline/config.yaml",
  allowedActions
)

builder.build(this, params.PLIB_PIPELINE)
