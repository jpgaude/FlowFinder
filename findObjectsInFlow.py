# for help getting all files in dir: https://stackoverflow.com/questions/11968976/list-files-only-in-the-current-directory

from bs4 import BeautifulSoup
from operator import itemgetter
import os
import json

objectToFlowMap = {"objectRefs": [], "errors": []} # Maps objects to unique lists of flows.
directory = '.'

def log_obj_ref(fileName, flowName, apiName, apiVersion, objectName):

  for objRef in objectToFlowMap["objectRefs"]:
    if objRef["objectName"] == objectName:
      for flowEntry in objRef["flows"]:
        if flowEntry["fileName"] == fileName:
          return
      objRef["flows"].append(create_flow_dictionary(fileName, flowName, apiName, apiVersion))
      return
  objectToFlowMap["objectRefs"].append({
    "objectName": objectName,
    "flows": [
      create_flow_dictionary(fileName, flowName, apiName, apiVersion)
    ]
  })

def create_flow_dictionary(fileName, flowName, apiName, apiVersion):
  return {
    "fileName": fileName,
    "flowLabelName": flowName,
    "flowApiName": apiName,
    "flowApiVersion": apiVersion
  }

flowFileNames = [f for f in os.listdir(directory) if (os.path.isfile(f) and f.endswith(".flow-meta.xml"))]

for flowFileName in flowFileNames:
  flowLabelName = ""
  flowApiName = None
  flowApiVersion = ""

  try:
    with open(flowFileName, 'r') as f:
      data = f.read()

    flow = BeautifulSoup(data, "xml").find("Flow")
    flowLabelName = flow.find("label", recursive=False).string
    flowApiVersion = flow.find("apiVersion").string
    if(flow.find("start") != None):
      flowStart = flow.find("start")
      if(flowStart.find("connector") != None):
        flowApiName = flowStart.find("connector").find("targetReference").string

    for objectTag in flow.find_all("object"):
      log_obj_ref(flowFileName, flowLabelName, flowApiName, flowApiVersion, objectTag.string)


  except Exception as e:
    objectToFlowMap["errors"].append({
      "message": "Could not parse the flow XML for '" + flowFileName + "'."
    })

objectToFlowMap["objectRefs"] = sorted(objectToFlowMap["objectRefs"], key=itemgetter("objectName"))
# for entry in objectToFlowMap["objectRefs"]:
#   entry["flows"] = sorted(entry["flows"], key=itemgetter("flowLabelName"))

with open("objectRefsInFlows.json", "w") as f:
  f.write(json.dumps(objectToFlowMap))
  f.close()