# for help getting all files in dir: https://stackoverflow.com/questions/11968976/list-files-only-in-the-current-directory

from bs4 import BeautifulSoup
from operator import itemgetter
import os
import json

objectToFlowMap = {"objectRefs": [], "errors": []} # Maps objects to unique lists of flows.
directory = '.'
objectsDictionary = {}

def where_variable_is_sobject(tag):
  if tag.name != "variables":
    return False
  if tag.find("dataType").string != "SObject":
    return False
  return True

def where_ref_tag(tag):
  return tag.name == "leftValueReference" or tag.name == "elementReference" or tag.name == "assignToReference" or tag.name == "targetReference"

def where_update_or_create_or_lookup(tag):
  return tag.name == "recordUpdates" or tag.name == "recordCreates" or tag.name == "recordLookups"

def log_obj_ref(fileName, flowName, apiName, apiVersion, objectName, fieldName):

  for flowEntry in objectToFlowMap["objectRefs"]:
    if(flowEntry["fileName"] == fileName):
      for objectEntry in flowEntry["objects"]:
        if(objectEntry["name"] == objectName):
          if fieldName not in objectEntry["fields"]:
            objectEntry["fields"].append(fieldName)
          return
      flowEntry["objects"].append(
        {
          "name": objectName, 
          "fields": [fieldName]
        }
      )
      return
  objectToFlowMap["objectRefs"].append({
    "fileName":fileName,
    "flowName": flowName,
    "apiName": apiName,
    "apiVersion": apiVersion,
    "objects": [
      {
        "name": objectName,
        "fields": [fieldName]
      }
    ]
  })

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
    
    flowStart = flow.find("start")
    if(flowStart != None):


      if(flowStart.find("connector") != None):
        flowApiName = flowStart.find("connector").find("targetReference").string

      recordObject = flowStart.find("object")
      if(recordObject != None):
        recordObjName = recordObject.string
        objectsDictionary["$Record"] = recordObjName
        for filterTag in flowStart.find_all("filters"):
          log_obj_ref(flowFileName, flowLabelName, flowApiName, flowApiVersion, recordObjName, filterTag.find("field").string)

    for variableTag in flow.find_all(where_variable_is_sobject):
      objectName = variableTag.find("objectType").string
      variableName = variableTag.find("name").string
      objectsDictionary[variableName] = objectName
    
    for refTag in flow.find_all(where_ref_tag):
      refValue = refTag.string
      if "." in refValue:
        objAndField = refValue.split(".", 1)
        objectName = objAndField[0]
        fieldName = objAndField[1]
        if(objectName in objectsDictionary): #objectName is not actually the object API name, but the name of a variable as it is varName.FieldAPIName__c in references.
          log_obj_ref(flowFileName, flowLabelName, flowApiName, flowApiVersion, objectsDictionary[objectName], fieldName)

    for tag in flow.find_all(where_update_or_create_or_lookup):
      objectTag = tag.find("object")
      if(objectTag != None):
        for filterTag in tag.find_all("filters"):
          fieldName = filterTag.find("field").string
          log_obj_ref(flowFileName, flowLabelName, flowApiName, flowApiVersion, objectTag.string, fieldName)
        
        for inputAssignmentsTag in tag.find_all("inputAssignments"):
          fieldName = inputAssignmentsTag.find("field").string
          log_obj_ref(flowFileName, flowLabelName, flowApiName, flowApiVersion, objectTag.string, fieldName)

  except Exception as e:
    objectToFlowMap["errors"].append({
      "message": "Could not parse the flow XML for '" + flowFileName + "'."
    })

objectToFlowMap["objectRefs"] = sorted(objectToFlowMap["objectRefs"], key=itemgetter("fileName"))
for entry in objectToFlowMap["objectRefs"]:
  entry["objects"] = sorted(entry["objects"], key=itemgetter("name"))
  for objectName in entry["objects"]:
    objectName["fields"] = sorted(objectName["fields"])

with open("objectRefsInFlows2.json", "w") as f:
  f.write(json.dumps(objectToFlowMap))
  f.close()