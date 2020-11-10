import sys, getopt
import csv
import json


usage = 'buildStock.py -f <function> -i <inputFile> -o <outputFile> \n \
function: convert2StockListJson, convert2BotJsonWithSyn, convert2BotJsonWithSynHom, \n \
buildKeywordList4TestSingular'

flow_prefix = "flow#"

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

def setNoWhenEmpty(str):
    if isNotEmpty(str) == False:
        return "no"
    return str

def getIntent(flowNum):
    num = flowNum.strip()
    flowIntentMapping = {
        "1": "itemNeedQuantity",
        "2": "itemNeedQuantity",
        "3": "itemNeedQuantity",
        "4": "itemNeedQuantity",
        "5": "itemNeedQuantity",
        "8": "itemNeedRepair",
        "9": "itemNeedRepair",
        "10": "informaitonService",
        "11": "serviceNeedMessage",
        "12": "serviceNeedCallBack",
        "14": "transferToFE"
    }
    try:
        flowIntentMapping.get(num)
    except NameError:
        print('Cannot find flow in flow_intent_mapping!')
    else:
        return flowIntentMapping.get(num)

def initIntentItemSlotTypes(intentName):
    return {
        "name": intentName,
        "version": "latest",
        "enumerationValues": [],
        "valueSelectionStrategy": "TOP_RESOLUTION"
    }

def convert2StockListJson(inputFile, outputFile):
    list = []
    with open(inputFile, mode='r') as request_file:
        csvFile = csv.DictReader(request_file, delimiter=",")
        for lines in csvFile:
            if isNotEmpty(lines["Item Singular"]):
                stock = {
                    "item": (try_ex(lambda: lines["Item Singular"])).lower(),
                    "type": setNoWhenEmpty((try_ex(lambda: lines["Type"])).lower()),
                    "department": setNoWhenEmpty((try_ex(lambda: lines["Department"])).lower()),
                    "cost": setNoWhenEmpty((try_ex(lambda: lines["Supply Fee"])).lower()),
                    "roomSection": setNoWhenEmpty((try_ex(lambda: lines["Section"])).lower()),
                    "inRoom": setNoWhenEmpty((try_ex(lambda: lines["In the room location"])).lower()),
                    "hasnone": "yes" if (try_ex(lambda: lines["Don't have (1)"])).lower() == "x" else "no"
                }
                list.append(stock)
                if (try_ex(lambda: lines["Item Singular"])).lower() != (try_ex(lambda: lines["Item Plural"])).lower():
                    stock = {
                        "item": (try_ex(lambda: lines["Item Plural"])).lower(),
                        "type": setNoWhenEmpty((try_ex(lambda: lines["Type"])).lower()),
                        "department": setNoWhenEmpty((try_ex(lambda: lines["Department"])).lower()),
                        "cost": setNoWhenEmpty((try_ex(lambda: lines["Supply Fee"])).lower()),
                        "roomSection": setNoWhenEmpty((try_ex(lambda: lines["Section"])).lower()),
                        "inRoom": setNoWhenEmpty((try_ex(lambda: lines["In the room location"])).lower()),
                        "hasnone": "yes" if (try_ex(lambda: lines["Don't have (1)"])).lower() == "x" else "no"
                    }
                    list.append(stock)

        with open(outputFile, 'w') as jsonFile:
            jsonFile.writelines(json.dumps(list,indent=4))
            jsonFile.close()

def buildKeywordList4TestSingular(inputFile, outputFile):
    list = []
    with open(inputFile, mode='r') as request_file:
        csvFile = csv.DictReader(request_file, delimiter=",")
        for lines in csvFile:
            if isNotEmpty(lines["Item Singular"]):
                list.append(try_ex(lambda: lines["Item Singular"]).lower())
                for iteS in (try_ex(lambda: lines["Synonyms Singular"]).lower()).split(","):
                    if iteS is not None and iteS != "":
                        list.append(iteS)
                for iteH in (try_ex(lambda: lines["Homonyms Singular"]).lower()).split(","):
                    if iteH is not None and iteH != "":
                        list.append(iteH)

        with open(outputFile, 'w') as jsonFile:
            jsonFile.writelines(json.dumps(list, indent=4))
            jsonFile.close()


# e.g. this is for enumerationValues within a slot
# take slot "itemNeedQuantity" for instance:
# {
# "name": "itemNeedQuantity",
# "version": "22",
# "enumerationValues": [result_of_convert2BotJsonWithSyn]
# }
# Warn! this result might need further modification due to not standardized source csv file
def convert2BotJsonWithSyn(inputFile, outputFile):
    intentList = {}
    with open(inputFile, mode='r') as request_file:
        csvFile = csv.DictReader(request_file, delimiter=",")
        for lines in csvFile:
            ele_Singular = {}
            # ele_plural = {}
            if isNotEmpty(lines["Item Singular"]):
                ele_Singular = {
                    "value": "",
                    "synonyms": ""
                }
                ele_Singular["value"] = try_ex(lambda: lines["Item Singular"].strip())
                syn = try_ex(lambda: lines["Synonyms Singular"]).split(',')
                if syn is not None:
                    ele_Singular["synonyms"] = [x.strip() for x in syn if x.strip()]

                # need to check plural exists and not equals to singular
                # ele_plural = {
                #     "value": "",
                #     "synonyms": ""
                # }
                # ele_plural["value"] = try_ex(lambda: lines["Item Plural"]),
                # ele_plural["synonyms"] = try_ex(lambda: lines["Synonyms Plural"]).split(',')
                # homonyms = try_ex(lambda: lines["Homonyms Plural"]).split(',')
                # if homonyms is not None and homonyms != []:
                #     ele_Singular["synonyms"] = ele_Singular["synonyms"] + homonyms

            flowNums = try_ex(lambda: lines["Process Flow Category"]).split(",")
            if len(flowNums) > 0:
                for idx in flowNums:
                    if idx is not None and idx is not "":
                        intentName = getIntent(str(idx))
                        if intentName is not None and intentName != "":
                            if intentName not in intentList:
                                intentList[intentName] = initIntentItemSlotTypes(intentName)
                            elif ele_Singular and ele_Singular not in intentList[intentName]["enumerationValues"]:
                                intentList[intentName]["enumerationValues"].append(ele_Singular)

                            # print(intentList)
                            # for ele_Plural

        with open(outputFile, 'w') as jsonFile:
            jsonFile.writelines(json.dumps((intentList),indent=4))
            jsonFile.close()

# For usage details, please refer to function "convert2BotJsonWithSyn"!!
def convert2BotJsonWithSynHom(inputFile, outputFile): # homonyms
    intentList = {}
    with open(inputFile, mode='r') as request_file:
        csvFile = csv.DictReader(request_file, delimiter=",")
        for lines in csvFile:
            ele_Singular = {}
            # ele_plural = {}
            if isNotEmpty(lines["Item Singular"]):
                ele_Singular = {
                    "value": "",
                    "synonyms": ""
                }
                ele_Singular["value"] = try_ex(lambda: lines["Item Singular"].strip())
                syn = try_ex(lambda: lines["Synonyms Singular"]).split(',')
                if syn is not None:
                    ele_Singular["synonyms"] = [x.strip() for x in syn if x.strip()]
                hom = try_ex(lambda: lines["Homonyms Singular"]).split(',')
                if hom is not None:
                    ele_Singular["synonyms"] += [x.strip() for x in hom if x.strip()]

                # need to check plural exists and not equals to singular
                # ele_plural = {
                #     "value": "",
                #     "synonyms": ""
                # }
                # ele_plural["value"] = try_ex(lambda: lines["Item Plural"]),
                # ele_plural["synonyms"] = try_ex(lambda: lines["Synonyms Plural"]).split(',')
                # homonyms = try_ex(lambda: lines["Homonyms Plural"]).split(',')
                # if homonyms is not None and homonyms != []:
                #     ele_Singular["synonyms"] = ele_Singular["synonyms"] + homonyms

            flowNums = try_ex(lambda: lines["Process Flow Category"]).split(",")
            if len(flowNums) > 0:
                for idx in flowNums:
                    if idx is not None and idx is not "":
                        intentName = getIntent(str(idx))
                        if intentName is not None and intentName != "":
                            if intentName not in intentList:
                                intentList[intentName] = initIntentItemSlotTypes(intentName)
                            elif ele_Singular and ele_Singular not in intentList[intentName]["enumerationValues"]:
                                intentList[intentName]["enumerationValues"].append(ele_Singular)

                            # print(intentList)
                            # for ele_Plural

        with open(outputFile, 'w') as jsonFile:
            jsonFile.writelines(json.dumps(intentList, indent=4))
            jsonFile.close()

def convert2BotJsonWithSynHomSP(inputFile, outputFile): # homonyms
    intentList = {}
    with open(inputFile, mode='r') as request_file:
        csvFile = csv.DictReader(request_file, delimiter=",")
        for lines in csvFile:
            ele_Singular = {}
            if isNotEmpty(lines["Item Singular"]):
                ele_Singular = {
                    "value": "",
                    "synonyms": ""
                }
                ele_Singular["value"] = try_ex(lambda: lines["Item Singular"].strip())
                syn = try_ex(lambda: lines["Synonyms Singular"]).split(',')
                if syn is not None:
                    ele_Singular["synonyms"] = [x.strip() for x in syn if x.strip()]
                hom = try_ex(lambda: lines["Homonyms Singular"]).split(',')
                if hom is not None:
                    ele_Singular["synonyms"] += [x.strip() for x in hom if x.strip()]

            ele_Plural = {}
            if isNotEmpty(lines["Item Plural"]):
                ele_Plural = {
                    "value": "",
                    "synonyms": ""
                }
                ele_Plural["value"] = try_ex(lambda: lines["Item Plural"].strip())
                syn = try_ex(lambda: lines["Synonyms Plural"]).split(',')
                if syn is not None:
                    ele_Plural["synonyms"] = [x.strip() for x in syn if x.strip()]
                hom = try_ex(lambda: lines["Homonyms Plural"]).split(',')
                if hom is not None:
                    ele_Plural["synonyms"] += [x.strip() for x in hom if x.strip()]


            flowNums = try_ex(lambda: lines["Process Flow Category"]).split(",")
            if len(flowNums) > 0:
                for idx in flowNums:
                    if idx is not None and idx is not "":
                        intentName = getIntent(str(idx))
                        if intentName is not None and intentName != "":
                            if intentName not in intentList:
                                intentList[intentName] = initIntentItemSlotTypes(intentName)
                            else:
                                if ele_Plural and ele_Plural not in intentList[intentName]["enumerationValues"]:
                                    intentList[intentName]["enumerationValues"].append(ele_Plural)
                                if ele_Singular and ele_Singular not in intentList[intentName]["enumerationValues"]:
                                    intentList[intentName]["enumerationValues"].append(ele_Singular)

        with open(outputFile, 'w') as jsonFile:
            jsonFile.writelines(json.dumps(intentList, indent=4))
            jsonFile.close()


def main(argv):
    function = ''
    inputFile = ''
    outputFile = ''

    try:
        opts, args = getopt.getopt(argv, "hf:i:o:",["func=","ifile=","ofile="])
    except getopt.GetoptError:
        print(usage)
        sys.exit(2)
    if len(sys.argv) != 7:
        print(usage)
        sys.exit(1)
    for opt, arg in opts:
        if opt in ("-f", "--func"):
            function = arg
        elif opt in ("-i", "--ifile"):
            inputFile = arg
        elif opt in ("-o", "--ofile"):
            outputFile = arg
    print('Calling funcion: '  + function + " with input file: " + inputFile + " and output file: " + outputFile)
    if isNotEmpty(function) and isNotEmpty(inputFile) and isNotEmpty(outputFile):
        if function == 'convert2StockListJson':
            print('output file: ' + outputFile)
            convert2StockListJson(inputFile, outputFile)
        elif function == 'convert2BotJsonWithSyn':
            convert2BotJsonWithSyn(inputFile, outputFile)
        elif function == 'convert2BotJsonWithSynHom':
            convert2BotJsonWithSynHom(inputFile, outputFile)
        elif function == 'convert2BotJsonWithSynHomSP':
            convert2BotJsonWithSynHomSP(inputFile, outputFile)
        elif function == 'buildKeywordList4TestSingular':
            buildKeywordList4TestSingular(inputFile, outputFile)
    else:
        print('Error: missing input parameters!')
        print(usage)



# main entry
if __name__ == "__main__":
    main(sys.argv[1:])