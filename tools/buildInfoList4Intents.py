import json
import sys, getopt
import pandas as pds
import re
import os

usage = 'buildInfoList4Intents.py -f <function> -i <inputFile> -o <outputFile> \n \
    function: infoList'

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

def initInfoElement():
    return {
        'name': '',
        'type': '',
        'openTime': '',
        'location': '',
        'specialNotes': ''
    }

def buildInfoList(inputFile):
    list = {}
    infoList_component = pds.read_excel(inputFile, sheet_name="infoDB", usecols=['Item', 'Name', 'Type', 'OpenTime', 'Location', 'SpecialNotes']).to_dict(orient='records')
    for lines in infoList_component:
        if isNotEmpty(lines["Item"]):
            item = lines['Item']
            ele = {
                'name': (try_ex(lambda: lines["Name"])),
                'type': (try_ex(lambda: lines["Type"])),
                'openTime': (try_ex(lambda: lines["OpenTime"])),
                'location': (try_ex(lambda: lines["Location"])),
                'specialNotes': (try_ex(lambda: lines["SpecialNotes"]))
            }
            if item not in list:
                list[item] = []
            (list[item]).append(ele)
    return list;

def writeOutput2File(output, outputFile):
    with open(outputFile, 'w') as jsonFile:
            jsonFile.writelines(json.dumps(output, indent=4))
            jsonFile.close()

def main(argv):
    inputFile = ''
    outputFile = ''
    function = '' # infoList
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
        if function == 'infoList':
            output = buildInfoList(inputFile)
            writeOutput2File(output, outputFile)
    else:
        print('Error: missing input parameters!')
        print(usage)



# main entry
if __name__ == "__main__":
    main(sys.argv[1:])