import logging
import json
import dateutil.parser
import datetime
import urllib3


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# --- Helper Functions ---

stockList = json.load(open('stockList.json', 'r'))
spMappingList = json.load(open('stockMapping.json', 'r'))
request_set = {
    "item_type": "",
    "item_num": "",
    "room_num": "",
    "service_type": "",
    "service_department": ""
}

# per item, update after validation, confirmation
def initItemValidationSet():
    return {
        'approvedQuest': [],
        'checkingQuest': '',
    }

def updateItemValidationSet(itemSet, approvedQuest, checkingQuest):
    itemSet = {
        'approvedQuest': itemSet['approvedQuest'].append(approvedQuest) if (approvedQuest is not None and approvedQuest != '') else [],
        'checkingQuest': checkingQuest
    }
    return itemSet


def initCleanOrderObj():
    return { "order": {"callId": "", "roomNumber": "", "robotVer": "", "requests": []}}

def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n

def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except KeyError:
        return None

def isvalid_item_type(item_type):
    # item_types = ['lotion', 'soap', 'shower gel', 'face towel', 'hand towel', 'bath towel', 'towel']
    # return item_type.lower() in item_types
    return searchStockListByItem(item_type)

def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False

def get_day_difference(later_date, earlier_date):
    later_datetime = dateutil.parser.parse(later_date).date()
    earlier_datetime = dateutil.parser.parse(earlier_date).date()
    return abs(later_datetime - earlier_datetime).days


def add_days(date, number_of_days):
    new_date = dateutil.parser.parse(date).date()
    new_date += datetime.timedelta(days=number_of_days)
    return new_date.strftime('%Y-%m-%d')


def build_validation_result(isvalid, violated_slot, message_content, validationSet):
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content},
        'validationSet': validationSet
    }


def validate_item_type(item_type, item_type_slot, session_attributes): # need to check if quantity already given
    logger.debug('validate_item_type item_type={}'.format(item_type))
    logger.debug('validate_item_type session_attributes={}'.format(session_attributes))

    vld_res = isvalid_item_type(item_type)
    logger.debug('validate_item_type - vld_res: {}'.format(vld_res))
    if item_type and vld_res['inStock'] == False and vld_res['details'] != "":
        #itemNeedQuantity: baby crib / wheelch
        logger.debug('have none!')
        return build_validation_result(
            False,
            item_type_slot,
            'I am very sorry, unfortunately we do not have {}! '
            'Anything else I can help you with?'.format(item_type),
            None
        )
    elif item_type and (vld_res['inStock'] == True):
        #itemNeedQuantity: rollaway beds
        if (vld_res['details']['cost'] != 'no'): # To Do
            logger.debug('extra cost!')
            # itemSet = session_attributes if session_attributes[''] is not None else initItemValidationSet() #???
            itemSet = initItemValidationSet() #???
            # continue to ask for cost
            return build_validation_result(
                True,
                item_type_slot,
                'Certainly. One {} will cost {} charging to your room. Are you OK with the charge?'.format(item_type, vld_res['details']['cost']),
                updateItemValidationSet(itemSet, None, 'cost')
            )
        else:
            #itemNeedQuantity: pillow
            if vld_res['details']['inRoom'] != 'no':
                logger.debug('item in the room')
                itemSet = initItemValidationSet() #???
                return build_validation_result(
                    True,
                    item_type_slot,
                    'Extra {} are usually stored {}. Could you please check and see if they are there?'.format(item_type, vld_res['details']['inRoom']),
                    updateItemValidationSet(itemSet, None, 'inRoom')
                )
            # itemNeedQuantity: bath towel
            return build_validation_result(True, None, None, None)


def searchStockListByItem(itemName):
    itemName = itemName.lower()
    if itemName in spMappingList:
        itemName = spMappingList[itemName]
    for item in stockList:
        if item['item'] == itemName:
            logger.debug('searchStockListByItem - itemStock: {} - itemName: {}'.format(item, itemName))
            if item['hasnone'] == "no":
                return {"inStock": True, "details": item}
            elif item['hasnone'] == "yes":
                return {"inStock": False, "details": item}
    return {"inStock": False, "details": ""}

def getCallID(intent_request):
    datet = datetime.datetime.now().strftime('%Y%m%d')
    call_id = '20000'
    fullcall_id = ''
    if 'userId' in intent_request:
        fullcall_id = intent_request['userId']
        call_id = ''.join([x for x in fullcall_id if x.isdigit()])
        call_id = datet + call_id[:8]
    return fullcall_id, call_id

def getRoomNum(session_attributes):
    room_num = ''
    if session_attributes is not None:
        if 'customerNumber' in session_attributes:
            # "sessionAttributes": {"Media.Sip.Headers.From": ".\"+18613583255551\" <sip:+18613583255551@0.0.0.0>;tag=0N1SZ9v8Z01ZN", ...}
            room_num = (session_attributes['Media.Sip.Headers.From']).split('\"')[1]
    room_num = '555'
    return room_num

def getTimeNow():
    return datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
