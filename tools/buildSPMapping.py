import sys, getopt
import csv
import json

usage = 'buildStock.py -f <function> -i <inputFile> -o <outputFile>'

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

def convert2SPMappingList(inputFile, outputFile):
    list = []
    with open(inputFile, mode='r') as request_file:
        csvFile = csv.DictReader(request_file, delimiter=",")
        for lines in csvFile:
            if isNotEmpty(lines["Item Plural"]):
                if isNotEmpty(lines["Item Plural"]):
                    obj = lines["Item Plural"] + ":" + lines["Item Singular"]
                else:
                    obj = lines["Item Plural"] + ":" + ""
                list.append(obj)

        with open(outputFile, 'w') as jsonFile:
            jsonFile.writelines(json.dumps(list,indent=4))
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
        if function == 'convert2SPMappingList':
            convert2SPMappingList(inputFile, outputFile)
    else:
        print('Error: missing input parameters!')

# main entry
if __name__ == "__main__":
    main(sys.argv[1:])