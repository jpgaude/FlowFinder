# for help getting all files in dir: https://stackoverflow.com/questions/11968976/list-files-only-in-the-current-directory

from bs4 import BeautifulSoup
import os
import json

object_name = 'WorkOrder'
field_name = 'Resource_Type__c'
directory = '.'
dmlOpperation = 'insert|update'
# directory = "C:/VSCode/HuesbyFullFlows/force-app/main/default/flows"

flowToReferencesDict = {"object": object_name, "field": field_name, "results": {}, "errors": []}

def where_record_update_is_specified_object(tag):
  if tag.name != "recordUpdates":
    return
  return tag.name == "recordUpdates" and ((tag.find("object") != None and tag.find("object").string == object_name) or ((tag.find("inputReference") != None and tag.find("inputReference").string == "$Record")))

def where_record_insert_is_specified_object(tag):
  if tag.name != "recordCreates":
    return
  return tag.name == "recordCreates" and ((tag.find("object") != None and tag.find("object").string == object_name) or ((tag.find("inputReference") != None and tag.find("inputReference").string == "$Record")))

def where_variable_is_specified_object(tag):
  return tag.name == "variables" and tag.find("objectType") != None and tag.find("objectType").string == object_name

def where_assignment_contains_ref(tag):
  if tag.name != "assignments":
    return False
  
  if tag.find_all(where_assign_to_reference_is_field_being_changed):
      return True
  
  return False    

def where_assign_to_reference_is_field_being_changed(tag):
  if tag.name != "assignToReference":
    return False
    
  object_and_field = tag.string.split('.')
  if(len(object_and_field) != 2):
    return False
  
  if object_and_field[0] not in object_var_names:
    return False
    
  return object_and_field[0] + "." + field_name == tag.string

def where_record_lookup_is_specified_object(tag):
  return tag.name == "recordLookups" and tag.find("object").string == object_name
  
def addRefToDictionary(flowName, ref, refType):
  if flowName not in flowToReferencesDict["results"]:
    flowToReferencesDict["results"][flowName] = {}

  # flowRefDict = flowToReferencesDict[flowName]
  
  if refType not in flowToReferencesDict["results"][flowName]:
    flowToReferencesDict["results"][flowName][refType] = []

  flowToReferencesDict["results"][flowName][refType].append(ref)

flowFileNames = [f for f in os.listdir(directory) if (os.path.isfile(f) and f.endswith(".flow-meta.xml"))]
# flowFileNames = [f for f in os.listdir(directory) if (os.path.isfile(os.path.join(directory, f)) and os.path.join(directory, f).endswith(".flow-meta.xml"))]

for flowFileName in flowFileNames:
  object_is_being_created_or_updated = False
  object_field_is_changed = False
  object_field_is_set = True
  start_element = None
  flow_status = ""
  object_var_names = []
  is_triggered_flow_for_object = False

  try:
    with open(flowFileName, 'r') as f:
      data = f.read()

    flow = BeautifulSoup(data, "xml")

    flow_status = flow.find("status").string
    start_element = flow.find("start")

    if start_element.find("recordTriggerType") :
      if start_element.find("object").string == object_name:
        is_triggered_flow_for_object = True
        object_var_names.append("$Record")

    if('update' in dmlOpperation):
      object_updates = flow.find_all(where_record_update_is_specified_object)

      if object_updates:
        for object_update in object_updates:
          for inputAssignment in object_update.find_all("inputAssignments"):

            if(inputAssignment.find("field").string == field_name):
              object_field_is_changed = True
              addRefToDictionary(flowFileName, object_update.find("name").string, "recordUpdates")              

        object_is_being_created_or_updated = True

    if('insert' in dmlOpperation):
      insert_objects = flow.find_all(where_record_insert_is_specified_object)

      if insert_objects:
        for insert_object in insert_objects:
          for inputAssignment in insert_object.find_all("inputAssignments"):

            if(inputAssignment.find("field").string == field_name):
              object_field_is_set = True
              addRefToDictionary(flowFileName, insert_object.find("name").string, "recordCreates")
        object_is_being_created_or_updated = True

    if not object_is_being_created_or_updated:
      continue

    for object_var in flow.find_all(where_variable_is_specified_object):
      object_var_names.append(object_var.find("name").string)

    lookup_elements = flow.find_all(where_record_lookup_is_specified_object)

    if lookup_elements:
      for lookup_element in lookup_elements:
        object_var_names.append(lookup_element.find("name").string)

    assignments = flow.find_all(where_assignment_contains_ref)

    if assignments:
      object_field_is_changed = True

    for assignment in assignments:
      addRefToDictionary(flowFileName, assignment.find("name").string, "assignments") 

  except Exception as e:
    flowToReferencesDict["errors"].append({
      "message": "Could not parse the flow XML for '" + flowFileName + "'."
    })

with open("result_" + object_name + "__" + field_name + ".json", "w") as f:
  f.write(json.dumps(flowToReferencesDict))
  f.close()