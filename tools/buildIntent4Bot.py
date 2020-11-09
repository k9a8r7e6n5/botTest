import json
import sys, getopt
import pandas as pds
import re
from collections import Counter
import os


usage = 'buildIntent4Bot.py -t <targetIntent> -i <inputFile> -o <outputFile> \n \
targetIntent: \n \
    generateAllSlotTypes to generate all slotTypes for all intents \n \
    intent name on SentencePattern.xlsx tab, "requestRepairItems_8,9"'

def initSlot():
    return {
        "sampleUtterances": [],
        "slotType": "", # slotKey: itemNeedRepair, MayI
        "slotTypeVersion": "latest",
        "obfuscationSetting": "NONE",
        "slotConstraint": "Optional",
        "valueElicitationPrompt": {
          "messages": [
            {
              "contentType": "PlainText",
              "content": ""
            }
          ],
          "maxAttempts": 2
        },
        "priority": "", # auto-increment
        "name": "" # slotKey: itemNeedRepair, MayI
    }

def initSlotWithSlotName4Amazons(slotName, slotType):
    if slotType.endswith('Snd'):
        slotType = slotType[:-3]

    return {
        "sampleUtterances": [],
        "slotType": slotType, # slotKey: itemNeedRepair, MayI
        "slotTypeVersion": "latest",
        "obfuscationSetting": "NONE",
        "slotConstraint": "Optional",
        "valueElicitationPrompt": {
          "messages": [
            {
              "contentType": "PlainText",
              "content": slotName.lower()
            }
          ],
          "maxAttempts": 2
        },
        "priority": "", # auto-increment
        "name": slotName # slotKey: itemNeedRepair, MayI
    }

def initSlotWithSlotName(slotName):
        slotkey = slotName
        if slotName.endswith('Snd'):
            slotkey=slotName[:-3]

        return {
        "sampleUtterances": [],
        "slotType": slotkey, # slotKey: itemNeedRepair, MayI
        "slotTypeVersion": "latest",
        "obfuscationSetting": "NONE",
        "slotConstraint": "Optional",
        "valueElicitationPrompt": {
          "messages": [
            {
              "contentType": "PlainText",
              "content": slotName.lower()
            }
          ],
          "maxAttempts": 2
        },
        "priority": "", # auto-increment
        "name": slotName # slotKey: itemNeedRepair, MayI
    }

def initIntent():
    return {
                "name": "", # intentName requestRepairItem
                "fulfillmentActivity": {
                    "type": "ReturnIntent"
                },
                "sampleUtterances": [], # intentName
                "slots": [] # depneds on the slots used by sample utterances per intent
            }

def initSlotTypeWithSlotName(slotName):
    return {
        "name": slotName,
        "version": "latest",
        "enumerationValues": [
            # {"value": ""}
        ]
    }

def initbot(botname):
    return {
        "metadata": {
            "schemaVersion": "1.0",
            "importType": "LEX",
            "importFormat": "JSON"
        },
        "resource": {
            "name": botname,
            "version": "latest",
            "intents": [],
            "slotTypes": [],
            "voiceId": "Joanna",
            "childDirected": 'false',
            "locale": "en-US",
            "idleSessionTTLInSeconds": '300',
            "clarificationPrompt": {
                "messages": [
                    {
                        "contentType": "PlainText",
                        "content": "My apologies.  Would you kindly repeat you just said?"
                    }
                ],
                "maxAttempts": '2'
            },
            "abortStatement": {
                "messages": [
                    {
                        "contentType": "PlainText",
                        "content": "I am not sure. I need someone at Front Desk to assist you on this. please Hold on for a second."
                    }
                ]
            },
            "detectSentiment": 'true',
            "enableModelImprovements": 'true'
        }
    }

def try_ex(func):
    try:
        return func()
    except KeyError:
        return None

def isNotEmpty(str):
    tmp = try_ex(lambda: str)
    if tmp is not None and tmp != '':
        return True
    return False

def getAmazonConstants(data_component):
    amazonList = {}
    for key in data_component.columns.ravel():
        list = try_ex(lambda: data_component[key])
        if list is not None and (list.dropna())[0].startswith("AMAZON."):
            amazonList[key] = (list.dropna())[0]
    print(amazonList)
    return amazonList

def generateTargetIntent(inputFile, outputFile):

    intentList = pds.read_excel(inputFile,None)
    data_component = pds.read_excel(inputFile, sheetname="component")

    output4IntentSlots = {"intents": []}
    for sheet_name in intentList.keys():
        if sheet_name == "component":
            continue

        slotRequiredList = []
        intentName = sheet_name.strip().split("_")[0]
        data_targetTab = pds.read_excel(inputFile, sheetname=sheet_name)
        targetIntentObj = initIntent()
        targetIntentObj["name"] = intentName
        for item in data_targetTab["Sentence"]:
            efItem = item.strip().replace('\u200b', '')
            if efItem is not None and efItem != "":
                targetIntentObj["sampleUtterances"].append(efItem)

                # find using keywords from sampleUtterances
                slotKeyList = re.findall(r"\{(\w+)\}", efItem)
                for idx in slotKeyList:
                    if idx not in slotRequiredList:
                        slotRequiredList.append(idx)

        amazonList = getAmazonConstants(data_component)
        priority_count = 1
        for key in slotRequiredList:
            key = key.strip()
            if key is not None and key != "" and key != "NaN":
                if try_ex(lambda: amazonList[key]) is not None and try_ex(lambda: data_component[key]) is not None:
                    slot = initSlotWithSlotName4Amazons(key, data_component[key].dropna()[0])
                    print("amazon slot: " + str(slot))
                else:
                    slot = initSlotWithSlotName(key)
                slot["priority"] = priority_count
                targetIntentObj["slots"].append(slot)
                priority_count += 1
        output4IntentSlots["intents"].append(targetIntentObj)

    with open(outputFile, 'w') as jsonFile:
        jsonFile.writelines(json.dumps(output4IntentSlots, indent=4))
        jsonFile.close()

def generateAllSlotTypes(inputFile, outputFile):
    output4IntentSlots = {"slotTypes": []}
    data_component = pds.read_excel(inputFile, sheet_name="component")
    amazonList = getAmazonConstants(data_component)

    for key in data_component.columns.ravel():
        #对item&service相关的词，由guestlist生成slot
        if key.startswith("item") or key.startswith("service") or key.startswith("informaiton"):
            continue
        if try_ex(lambda: data_component[key]) is not None and try_ex(lambda: amazonList[key]) is None:
            slotIndice = initSlotTypeWithSlotName(key)
            precise_data_component_key = ""
            if try_ex(lambda: data_component[key]) is not None:
                precise_data_component_key = try_ex(lambda: data_component[key]).dropna()
            else:
                print("Cannot find keyword in 'component' tab: " + key)
            for smp in precise_data_component_key:
                smp = str(smp).strip().replace('\u200b', '')
                if smp is not None and smp != "":
                    slotIndice["enumerationValues"].append({"value": smp})
            output4IntentSlots["slotTypes"].append(slotIndice)
        else:
           print("For Amazon Constants: " + (data_component[key].dropna())[0])

    with open(outputFile, 'w') as jsonFile:
                jsonFile.writelines(json.dumps(output4IntentSlots, indent=4))
                jsonFile.close()

def generateBot(botname, outputFile):
    bot = initbot(botname)
    output4bot = bot

    #intent
    with open("intent_all.json", 'r') as jsonFile_intent_all:
        intent_all = json.loads(jsonFile_intent_all.read())["intents"]
        jsonFile_intent_all.close()
        #print("intent_all is %s " % intent_all)
    output4bot["resource"]["intents"] = intent_all

    #slot used for sentence
    with open("slot_woItems.json", 'r') as jsonFile_slot_woItems:
        slot_woItems = json.loads(jsonFile_slot_woItems.read())["slotTypes"]
        jsonFile_slot_woItems.close()
        #print("slot_woItems is %s " % slot_woItems)

    slottypes = slot_woItems
    #slot used for items
    with open("slot_itemsOnly.json", 'r') as jsonFile_slot_itemsOnly:
        slot_itemsOnly = json.loads(jsonFile_slot_itemsOnly.read())
        jsonFile_slot_itemsOnly.close()
        #print("slot_itemsOnly is %s " % slot_itemsOnly)

    for json_data in slot_itemsOnly:
        #if isinstance(json_data, dict):
        #print(slot_itemsOnly[json_data])
            # 向json文件中写入新的键值对
        slottypes.append(slot_itemsOnly[json_data])

    #merge the two slot
    #slottypes = slot_woItems.append(slot_itemsOnly)
    output4bot["resource"]["slotTypes"] = slottypes

    with open(outputFile, 'w') as jsonFile:
                jsonFile.writelines(json.dumps(output4bot, indent=4))
                jsonFile.close()

def main(argv):
    targetIntent = ''
    inputFile = ''
    outputFile = ''

    try:
        opts, args = getopt.getopt(argv, "ht:i:o:",["target=","ifile=","ofile="])
    except getopt.GetoptError:
        print(usage)
        sys.exit(2)
    if len(sys.argv) != 7:
        print(usage)
        sys.exit(1)
    for opt, arg in opts:
        if opt in ("-t", "--target"):
            targetIntent = arg
        elif opt in ("-i", "--ifile"):
            inputFile = arg
        elif opt in ("-o", "--ofile"):
            outputFile = arg
    print('Calling target intent: '  + targetIntent + " with input file: " + inputFile + " and output file: " + outputFile)
    if isNotEmpty(targetIntent) and isNotEmpty(inputFile) and isNotEmpty(outputFile):
        if targetIntent == "generateAllUsedSlotTypes":
            generateAllUsedSlotTypes(inputFile, outputFile)
        elif targetIntent == "generateAllSlotTypes":
            generateAllSlotTypes(inputFile, outputFile)
        elif targetIntent == "findDuplicatesInSlot":
            findDuplicatesInSlot(inputFile)
        elif targetIntent == "generateTargetIntent":
            generateTargetIntent(inputFile, outputFile)
        elif targetIntent == "generateBot":
            generateBot(inputFile, outputFile)
        else:
            print('Error: not support')
    else:
        print('Error: missing input parameters!')
        print(usage)



# main entry
if __name__ == "__main__":
    main(sys.argv[1:])