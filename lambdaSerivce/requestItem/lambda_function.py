import json
import time
import os
import logging
import boto3
import urllib3
import re

from botocore.exceptions import ClientError
from services import *
from lex_response import *


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

region = "us-east-1"
originationNumber = "+12085082652"

# The recipient's phone number.  For best results, you should specify the
# phone number in E.164 format.
destinationNumber = "+17703296130"
message = ("This is a sample message to test the integration of sms and bot")

# applicationId = "73e717850bf041aaaa5e8ed9d16dcdd0"
applicationId = "d18093218356489698690c035998bfc7"


# The type of SMS message that you want to send. If you plan to send
# time-sensitive content, specify TRANSACTIONAL. If you plan to send
# marketing-related content, specify PROMOTIONAL.
messageType = "PROMOTIONAL"

# The registered keyword associated with the originating short code.
registeredKeyword = "myKeyword"

senderId = "HotelService"
###########################################
SENDER = "zhaoliang <liyingfu121@gmail.com>"
TOADDRESS = "liyingfu121@gmail.com"
SUBJECT = "Amazon Pinpoint Test (SDK for Python (Boto 3))"
BODY_TEXT = """Amazon Pinpoint Test (SDK for Python)
-------------------------------------
This email was sent with Amazon Pinpoint using the AWS SDK for Python (Boto 3).
For more information, see https:#aws.amazon.com/sdk-for-python/
            """

BODY_HTML = """<html>
<head></head>
<body>
  <h1>Amazon Pinpoint Test (SDK for Python)</h1>
  <p>This email was sent with
    <a href='https:#aws.amazon.com/pinpoint/'>Amazon Pinpoint</a> using the
    <a href='https:#aws.amazon.com/sdk-for-python/'>
      AWS SDK for Python (Boto 3)</a>.</p>
</body>
</html>
            """

CHARSET = "UTF-8"

###################################################
# hold all confirmed requests
finalOrder = initCleanOrderObj()

# Create a new client and specify a region.
clientPinpoint = boto3.client('pinpoint',region_name=region)
clientConnect = boto3.client('connect',region_name=region)
clientlex = boto3.client('lex-runtime',region_name=region)

#lex functions
def lex_get_session(call_id):
    response = clientlex.get_session(
        botName='HotelService',
        botAlias='HotelService',
        userId=call_id
    )
    return response

# get slot
def get_current_slots(intent_request):
    return intent_request['currentIntent']['slots']

# get callerID
def getCallerID():
    response = clientConnect.get_contact_attributes(
        InstanceId='f8825c02-7e0c-4207-985d-1bc44006a6ec',
        InitialContactId='2925d685-6d22-4954-9cc7-0a19f53ff1f9'
    )
    return response

def buildSMSBody(orderId):
    link_str = "http://ibot.hibaysoft.com:33580/msg/" + str(orderId)
    return link_str

# send short message by pinpoint
def sendSMS(msg):
    try:
        response = clientPinpoint.send_messages(
            ApplicationId=applicationId,
            MessageRequest={
                'Addresses': {
                    destinationNumber: {
                        'ChannelType': 'SMS'
                    }
                },
                'MessageConfiguration': {
                    'SMSMessage': {
                        'Body': msg,
                        'Keyword': '',
                        'MessageType': messageType,
                        'OriginationNumber': '',
                        'SenderId': ''
                    }
                }
            }
        )

    except ClientError as e:
        print(e.response['Error']['Message'])
        return None
    else:
        print("Message sent! Message ID: "
                + response['MessageResponse']['Result'][destinationNumber]['MessageId'])
        return response

## send a email by pinpoint
def sendmail(subj, body_html):
    try:
        response = clientPinpoint.send_messages(
            ApplicationId=applicationId,
            MessageRequest={
                'Addresses': {
                    TOADDRESS: {
                         'ChannelType': 'EMAIL'
                    }
                },
                'MessageConfiguration': {
                    'EmailMessage': {
                        'FromAddress': SENDER,
                        'SimpleEmail': {
                            'Subject': {
                                'Charset': CHARSET,
                                'Data': subj
                            },
                            'HtmlPart': {
                                'Charset': CHARSET,
                                'Data': body_html
                            },
                            'TextPart': {
                                'Charset': CHARSET,
                                'Data': BODY_TEXT
                            }
                        }
                    }
                }
            }
        )
    except ClientError as e:
        return None
    else:
        return response

def cancelAllRequests(session_attributes):
    return session_attributes['confirmedItems'].clear()

def cancelSomeRequests(session_attributes, itemType, itemNum):
    tmp = session_attributes['confirmedItems']
    for ele in tmp:
        if ele['itemNeedQuantity'] == itemType and ele['quantityList'] == itemNum:
            tmp.remove(ele)
            return tmp

def buildFinalOrder(session_attributes, fullcall_id):
    confirmedItems = try_ex(lambda: session_attributes['confirmedItems'])
    if confirmedItems is None:
        return None
    list = json.loads(confirmedItems)
    for ele in list:
        itemType = try_ex(lambda: ele['itemNeedQuantity'])
        item = searchStockListByItem(itemType)['details']
        try:
            item
        except NameError:
            logger.debug('createNewOrderForAllRequests - not found item!')
        else:
            logger.debug('createNewOrderForAllRequests - found item: {}'.format(item))
            slice = {
                "dept": try_ex(lambda: item["department"]),
                "service": try_ex(lambda: item["type"]),
                "subCategory": itemType,
                "quantity": try_ex(lambda: ele['quantityList']),
                "escalation": "None",
                "requestTime": try_ex(lambda: ele['time']),
                "completionTime": "",
                "worker":"Alex",
                "status":"In Progress",
                "comments": '',
                "callIdFull": fullcall_id
            }
            finalOrder["order"]["requests"].append(slice)
    return finalOrder

def delOrderSlice(itemType, comment, quantity, fullcallid, finalOrder):
    for obj in finalOrder['requests']:
        if obj['subCategory'] == itemType \
            and obj['quantity'] == quantity \
            and obj['callIdFull'] == fullcallid \
            and obj['comments'] == comment:
            finalOrder['requests'].remove(obj)

def createFinalOrder(call_id, room, botversion, finalOrder):
    data = finalOrder
    http = urllib3.PoolManager(num_pools=1, headers={'User-Agent': 'hotelbot'})
    orderUrl = "http://139.129.117.119:33598/hotel/order/order"
    data['order']['callId'] = call_id
    data['order']['roomNumber'] = room
    data['order']['robotVer'] = botversion
    dataJson = json.dumps(data)
    resp = http.request('POST', orderUrl, body=dataJson, timeout=5, retries=5)
    result = json.loads(resp.data)
    # logger.debug('create order, id={} '.format(result))
    # return result["orderId"]
    return "1234567890"

def sendOrder(order, call_id, room_num, bot_version):
    if order is not None:
        # sms_str = "[Guest Services]Please send " + item_number + " "  + item_type + " to room (#" + room_num + ") Thank you!"
        sms_str = "[Guest Services] Please take care of below request: " + repr(order['order']['requests']) + " for room (#" + room_num + "). Thank you!"
        order_id = createFinalOrder(call_id, room_num, bot_version, order)
        email_subj = sms_str + " Please click here (Request#" + str(order_id) + ") after it is done." # need to add all requests in email
        email_body_here = buildSMSBody(order_id)
        sendmail(email_subj, email_body_here)
        sms_body = sms_str + " Please click " +  email_body_here + " ( Request#" + str(order_id) + " ) after it is done."

# --- Helpers that build all of the responses ---
def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }

def confirm_intent(session_attributes, intent_name, slots, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': message
        }
    }

def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response

def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

def elicit_intent(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitIntent',
            'slots': slots
        }
    }

def close_default(session_attributes, fulfillment_state):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state
        }
    }

    return response

def build_confirm_msg(session_attributes):
    confirmAll = 'No request yet'
    if session_attributes == {}:
        return confirmAll
    confirmedItems = []
    if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
        confirmedItems = json.loads(session_attributes['confirmedItems'])
        logger.debug('requestItem is {}'.format(confirmedItems))
        confirmMsg = confirmSend
        confirmMsgEnd = confirmSendEnd
        confirmMsgBody = ''
        for ele in confirmedItems:
            itemType = try_ex(lambda: ele['itemNeedQuantity'])
            if ele['quantityList'] == '':
                confirmMsgBody += itemType + ', '
            else:
                confirmMsgBody += ele['quantityList'] + ' ' + itemType + ', '
        #confirmMsgBody = 'a bath towel,a hand towel,a body towel,'
        confirmMsgBody = re.sub(',(?=((?!,).)*$)','',confirmMsgBody)
        confirmMsgBody = re.sub(',(?=((?!,).)*$)',' and ',confirmMsgBody)
        confirmAll = confirmMsg + confirmMsgBody + confirmMsgEnd
    logger.debug('confirm all the thing is: {}'.format(confirmAll))
    return confirmAll

""" --- Functions that control the bot's behavior --- """
def initReservation(item, number, roomnumber):
    return {
        'item': item,
        'quantityList': number if number is not None else '',
        'roomnumber': roomnumber if roomnumber is not None else '',
        'time': getTimeNow()
    }

def removeLastConfirmedItem(session_attributes):
    confirmedItems = []
    if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
        confirmedItems = json.loads(session_attributes['confirmedItems'])
        #delete last confirm item
        confirmedItems.pop()
    return confirmedItems

def addConfirmedItem(session_attributes, reservation):
    confirmedItems = []
    if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
        confirmedItems = json.loads(session_attributes['confirmedItems'])
    confirmedItems.append(reservation)
    return confirmedItems

def request_item(intent_request):
    """
    Performs dialog management and fulfillment for booking a hotel.
    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """

    intent_name = intent_request['currentIntent']['name']

    if intent_name == 'requestItemQuantity':
        # Get item type
        item_type = try_ex(lambda: intent_request['currentIntent']['slots']['itemNeedQuantity'])
        item_number = try_ex(lambda: intent_request['currentIntent']['slots']['quantityList'])
        item_type_slot = 'itemNeedQuantity'
        logger.debug('request_item item_type={}'.format(item_type))
        # To make sure item type is not None
        if item_type is None:
            logger.debug('request_item - Bot can not identify your intent/slot. Transfer to FrontDesk after trying for two times')
            return delegate(
                intent_request['sessionAttributes'],
                {}
            )

    if item_number:
        confirmType = confirmItemType + item_number + ' ' + item_type + confirmItemTypeAnythingElse
        reservation = {
            'itemNeedQuantity': item_type,
            'quantityList': item_number,
            'validationSet': '',
            'time': getTimeNow()
        }
    else:
        confirmType = confirmItemType + item_type + confirmItemTypeAnythingElse
        reservation = {
            'itemNeedQuantity': item_type,
            'quantityList': '',
            'validationSet': '',
            'time': getTimeNow()
        }

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    session_attributes['lastIntent'] = intent_request['currentIntent']['name']

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_current_slots(intent_request)

        # item type validation check
        validation_result = validate_item_type(item_type, item_type_slot, session_attributes)
        #logger.debug('lambda func: validation_result: {}'.format(validation_result))
        #add validation flag
        reservation['validationSet'] = validation_result['validationSet'] # includes approvedQuest, checkingQuest
        session_attributes['currentReservation'] = json.dumps(reservation)
        logger.debug('request_item - dialogcodehook - currentReservation: {}'.format(session_attributes['currentReservation']))

        # validate haveNone,cost,in room,then close the session.
        if validation_result['message']['content']:
            return close(intent_request['sessionAttributes'],
                                   'Fulfilled',
                                   validation_result['message'])

        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        return delegate(output_session_attributes, get_current_slots(intent_request))

    if intent_request['invocationSource'] == 'FulfillmentCodeHook':

        inputsentence = try_ex(lambda: intent_request['inputTranscript'])
        if inputsentence is not None:
            inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
            if inputsentenceHis is not None:
                inputsentenceHis = inputsentenceHis + "," + inputsentence
            else:
                inputsentenceHis = inputsentence

            session_attributes['inputsentenceHis'] = inputsentenceHis
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']

        confirmedItems = []
        if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
            confirmedItems = json.loads(session_attributes['confirmedItems'])
        confirmedItems.append(reservation)
        session_attributes['confirmedItems'] = json.dumps(confirmedItems)

        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': confirmType
            }
        )

def requestRepairItems(intent_request):
    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        inputsentence = try_ex(lambda: intent_request['inputTranscript'])
        if inputsentence is not None:
            inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
            if inputsentenceHis is not None:
                inputsentenceHis = inputsentenceHis + "," + inputsentence
            else:
                inputsentenceHis = inputsentence

            session_attributes['inputsentenceHis'] = inputsentenceHis
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']

            slots = get_current_slots(intent_request)
            itemNeedRepair = try_ex(lambda: slots['itemNeedRepair'])
            itemNeedRepairSnd = try_ex(lambda: slots['itemNeedRepairSnd'])
            newone = try_ex(lambda: slots['newone'])
            new = try_ex(lambda: slots['new'])
            change = try_ex(lambda: slots['change'])
            bechanged = try_ex(lambda: slots['bechanged'])
            send = try_ex(lambda: slots['send'])
            miss = try_ex(lambda: slots['miss'])
            need = try_ex(lambda: slots['need'])
            ''' instructions, where, how'''
            itemInfo = try_ex(lambda: slots['itemInfo'])
            quantityList = try_ex(lambda: slots['quantityList']) if try_ex(lambda: slots['quantityList']) is not None else ''
            roomnumber = try_ex(lambda: slots['roomnumber'])
            toWhere = try_ex(lambda: slots['toWhere'])

            logger.debug('requestRepairItem - quantityList: {}'.format(quantityList))

            returnMsg, reservationItem = '', ''
            reservation = {}
            locationInfo, replacement = '', ''
            if (itemNeedRepair is not None and (new is not None or newone is not None or itemNeedRepairSnd is not None \
                or bechanged is not None or change is not None or send is not None or miss is not None or need is not None \
                or '' != quantityList)):
                if itemNeedRepairSnd is not None:
                    replacement = itemNeedRepairSnd
                else:
                    if ('a' != quantityList and 'one' != quantityList and '' != quantityList):
                        replacement = ' new ones'
                    else:
                        replacement = ' new one '
                if (toWhere is not None):
                    locationInfo = " to " + toWhere
                if (roomnumber is not None):
                    locationInfo = " in room " + roomnumber
                reservationItem = 'complain about ' + itemNeedRepair + ' and need ' + quantityList + ' ' + replacement
                reservation = initReservation('RepairItem: ' + reservationItem , quantityList, locationInfo)
                returnMsg = 'You ' + reservationItem + locationInfo
            elif (itemNeedRepair is not None and itemInfo is not None):
                reservationItem = 'need information about ' + itemNeedRepair
                reservation = initReservation('RepairItem: ' + reservationItem , quantityList, locationInfo)
                returnMsg = 'You ' + reservationItem + locationInfo
            elif (itemNeedRepair is not None and (new is None and newone is None and itemNeedRepairSnd is None \
                and bechanged is None and change is None and send is None)):
                reservationItem = 'complain about ' + itemNeedRepair + ' and need repair'
                reservation = initReservation('RepairItem: ' + reservationItem , quantityList, locationInfo)
                returnMsg = 'You ' + reservationItem + locationInfo

            confirmedItems = []
            if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
                confirmedItems = json.loads(session_attributes['confirmedItems'])
            confirmedItems.append(reservation)
            session_attributes['confirmedItems'] = json.dumps(confirmedItems)
            logger.debug("requestCallBack - session_attributes: {}".format(session_attributes))
            return close(
                session_attributes,
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': returnMsg + confirmItemTypeAnythingElse
                }
            )

def requestReplaceItems(intent_request):
    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        inputsentence = try_ex(lambda: intent_request['inputTranscript'])
        if inputsentence is not None:
            inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
            if inputsentenceHis is not None:
                inputsentenceHis = inputsentenceHis + "," + inputsentence
            else:
                inputsentenceHis = inputsentence

            session_attributes['inputsentenceHis'] = inputsentenceHis
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']

            slots = get_current_slots(intent_request)
            itemNeedReplace = try_ex(lambda: slots['​itemNeedReplace'])
            returnMsg = ""
            reservation = {}
            if (itemNeedReplace is not None):
                reservation = initReservation('ReplaceItem: ' + itemNeedReplace, None, None)
                returnMsg = "You ask to replace " + itemNeedReplace

            confirmedItems = []
            if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
                confirmedItems = json.loads(session_attributes['confirmedItems'])
            confirmedItems.append(reservation)
            session_attributes['confirmedItems'] = json.dumps(confirmedItems)
            logger.debug("requestReplaceItems - session_attributes: {}".format(session_attributes))
            return close(
                session_attributes,
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': returnMsg + confirmItemTypeAnythingElse
                }
            )

def requestInformation(intent_request):
    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

        passwordFlag = 'true'
        inputsentence = try_ex(lambda: intent_request['inputTranscript'])
        if inputsentence is not None:
            if 'password' in inputsentence:
                passwordFlag = 'true'
            inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
            if inputsentenceHis is not None:
                inputsentenceHis = inputsentenceHis + "," + inputsentence
            else:
                inputsentenceHis = inputsentence

            session_attributes['inputsentenceHis'] = inputsentenceHis
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']

            slots = get_current_slots(intent_request)
            informationServie = try_ex(lambda: slots['​informationServie'])
            internet = try_ex(lambda: slots['​internet'])

            returnMsg = 'vimin'
            reservation = {}

            #if internet is not None:
            if passwordFlag:
                wifiPassword = infoList['WIFI password'][0]['specialNotes']
                returnMsg = wifiPassword
            else:
                returnMsg = 'You would like check intenet status'

            logger.debug("requestInformation - searchInfoListByItem:{}".format(returnMsg))
            '''
            if (serviceNeedCallBack is not None):
                reservation = initReservation(serviceNeedCallBack, None, None)
                returnMsg = "You ask for " + serviceNeedCallBack + " and need Front Office to call you back"
            else:
                reservation = initReservation("complaint: " + inputsentence, None, None)
                returnMsg = "You would like to make a complaint that " + inputsentence + ". And you need Front Office to call you back."

            confirmedItems = []
            if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
                confirmedItems = json.loads(session_attributes['confirmedItems'])
            confirmedItems.append(reservation)
            session_attributes['confirmedItems'] = json.dumps(confirmedItems)
            logger.debug("requestCallBack - session_attributes: {}".format(session_attributes))
            '''
            return close(
                session_attributes,
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': returnMsg + confirmItemTypeAnythingElse
                }
            )

def getConfirmInfo(slots, inputsentence):
    serviceNeedMessage = try_ex(lambda: slots['serviceNeedMessage'])
    roomnumber = try_ex(lambda: slots['roomnumber']) if try_ex(lambda: slots['roomnumber']) is not None else ''
    beserviced = try_ex(lambda: slots['beserviced'])
    serve = try_ex(lambda: slots['serve'])
    dirty = try_ex(lambda: slots['dirty'])
    itemNeedQuantity = try_ex(lambda: slots['itemNeedQuantity'])
    beremoved = try_ex(lambda: slots['beremoved'])
    remove = try_ex(lambda: slots['remove'])
    pickup = try_ex(lambda: slots['pickup'])
    bepickedup = try_ex(lambda: slots['bepickedup'])
    quantityList = try_ex(lambda: slots['quantityList']) if try_ex(lambda: slots['quantityList']) is not None else ''

    returnMsg = ''
    reservation = {}
    roomInfo = ''
    if ((remove is not None or beremoved is not None) and dirty is not None and itemNeedQuantity is not None):
        roomInfo = " in room" + roomnumber if roomnumber is not None else ''
        reservation = initReservation("remove dirty " + itemNeedQuantity, quantityList, roomnumber)
        returnMsg = "You need to remove dirty " + quantityList + " "+ itemNeedQuantity + roomInfo
    elif (serviceNeedMessage is not None):
        reservation = initReservation(serviceNeedMessage, None, roomnumber)
        returnMsg = "You need " + serviceNeedMessage + roomInfo
    elif (pickup is not None or bepickedup is not None):
        reservation = initReservation("something to be picked", None, roomnumber)
        returnMsg = "You need something to be picked up " + roomInfo
    elif (serve is not None or beserviced is not None or "sweep" in inputsentence):
        reservation = initReservation("room to be served", None, roomnumber)
        returnMsg = "You need room " + roomnumber + " to be served"
    else:
        ''' some sentence without keywords'''
        reservation = initReservation("MessageToDeliver: " + inputsentence, None, None)
        returnMsg = "You said '" + inputsentence + "'"
    response = {
        'returnMsg': returnMsg,
        'reservation': reservation
    }
    return response

def addConfirmItem(session_attributes, reservation):
    confirmedItems = []
    if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
        confirmedItems = json.loads(session_attributes['confirmedItems'])
    confirmedItems.append(reservation)
    return confirmedItems

def updateInputSentenceHis(session_attributes, inputsentence):
    inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
    if inputsentenceHis is not None:
        inputsentenceHis = inputsentenceHis + "," + inputsentence
    else:
        inputsentenceHis = inputsentence
    return inputsentenceHis

def requestMessageDeliver(intent_request):
    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        inputsentence = try_ex(lambda: intent_request['inputTranscript'])
        if inputsentence is not None:
            session_attributes['inputsentenceHis'] = updateInputSentenceHis(session_attributes, inputsentence)
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']
            slots = get_current_slots(intent_request)
            confirmInfo = getConfirmInfo(slots, inputsentence)
            confirmedItems = addConfirmedItem(session_attributes, confirmInfo['reservation'])
            session_attributes['confirmedItems'] = json.dumps(confirmedItems)
            logger.debug("requestMessageDeliver - session_attributes: {}".format(session_attributes))
            return close(
                session_attributes,
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': confirmInfo['returnMsg'] + confirmItemTypeAnythingElse
                }
            )

def requestCallBack(intent_request):
    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        inputsentence = try_ex(lambda: intent_request['inputTranscript'])
        if inputsentence is not None:
            inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
            if inputsentenceHis is not None:
                inputsentenceHis = inputsentenceHis + "," + inputsentence
            else:
                inputsentenceHis = inputsentence

            session_attributes['inputsentenceHis'] = inputsentenceHis
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']

            slots = get_current_slots(intent_request)
            serviceNeedCallBack = try_ex(lambda: slots['​serviceNeedCallBack'])
            returnMsg = ""
            reservation = {}
            if (serviceNeedCallBack is not None):
                reservation = initReservation(serviceNeedCallBack, None, None)
                returnMsg = "You ask for " + serviceNeedCallBack + " and need Front Office to call you back"
            else:
                reservation = initReservation("complaint: " + inputsentence, None, None)
                returnMsg = "You would like to make a complaint that " + inputsentence + ". And you need Front Office to call you back."

            confirmedItems = []
            if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
                confirmedItems = json.loads(session_attributes['confirmedItems'])
            confirmedItems.append(reservation)
            session_attributes['confirmedItems'] = json.dumps(confirmedItems)
            logger.debug("requestCallBack - session_attributes: {}".format(session_attributes))
            return close(
                session_attributes,
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': returnMsg + confirmItemTypeAnythingElse
                }
            )

def byebye(intent_request):
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    if session_attributes != {}:
        room = getRoomNum(session_attributes)
        fullcall_id, call_id = getCallID(intent_request)
        #order = buildFinalOrder(session_attributes, fullcall_id)
        #sendOrder(order, call_id, room, '5') # check how to get bot version?
        # TODO: need to clear item_type, item_number, session_attributes
        session_attributes.clear()
        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': 'Have a good day!'
            }
        )
    else:
        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': 'Have a good day!'
            }
        )

def confirm_yes(intent_request):
    """
    Performs dialog management and fulfillment for booking a car.
    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    lastIntent = try_ex(lambda: session_attributes['lastIntent'])
    session_attributes['lastIntent'] = lastIntent

    logger.debug('confim_yes session_attributes[currentReservation] = {}'.format(session_attributes['currentReservation']))

    # add for flow #2: cost and #3:in room
    checkingReservation = {}
    if try_ex(lambda: session_attributes['currentReservation']) is not None and try_ex(lambda: session_attributes['currentReservation']) != '':
        checkingReservation = json.loads(session_attributes['currentReservation'])
        logger.debug('confim_yes checkingReservation {}'.format(checkingReservation))

    if lastIntent == 'requestItemQuantity':
        checkingSet = ''
        checkingContent = ''
        if checkingReservation:
            checkingSet = try_ex(lambda: checkingReservation['validationSet'])
            if checkingSet:
                checkingContent = try_ex(lambda: checkingSet['checkingQuest']) if try_ex(lambda: checkingSet['checkingQuest']) is not None else ''
            item_type = try_ex(lambda: checkingReservation['itemNeedQuantity'])
            item_number = try_ex(lambda: checkingReservation['quantityList']) if try_ex(lambda: checkingReservation['quantityList']) is not None else ''
        if checkingContent == 'inRoom':
            validationSet = json.loads(session_attributes['currentReservation'])['validationSet']
            checkingReservation['validationSet'] = updateItemValidationSet(validationSet, 'inRoom', None) # clear inRoom check status, make inRoom approve status
            session_attributes['currentReservation'] = json.dumps(checkingReservation)

            confirmedItems = []
            if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
                confirmedItems = json.loads(session_attributes['confirmedItems'])
                # delete last confirmedItems if last intent is change intents
                if lastIntent == 'confirmNoNeedQuantity' or lastIntent == 'confirmNoNeedQuantityClarify' or lastIntent == 'confirmNoWoQuantity':
                    confirmedItems.pop()
                session_attributes['confirmedItems'] = json.dumps(confirmedItems)
                logger.debug('confirm_yes - if inRoom is yes, print session_attributes[confirmedItems] = {} '.format(session_attributes['confirmedItems']))

            session_attributes['lastIntent'] = intent_request['currentIntent']['name']
            # cofirm yes for item in the room, close the session.
            return close(
                session_attributes,
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': anythingElse
                }
            )
        elif checkingContent == 'cost':
            validationSet = json.loads(session_attributes['currentReservation'])['validationSet']
            checkingReservation['validationSet'] = updateItemValidationSet(validationSet, 'cost', None) # clear inRoom check status, make inRoom approve status
            session_attributes['currentReservation'] = json.dumps(checkingReservation)
            # fake a ConfirmedItem for item customer want to charge
            reservation = {
                'itemNeedQuantity': item_type,
                'quantityList': '',
                'time': getTimeNow()
            }
            confirmedItems = []
            if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
                confirmedItems = json.loads(session_attributes['confirmedItems'])
                # delete last confirmedItems if last intent is change intents
                if lastIntent == 'confirmNoNeedQuantity' or lastIntent == 'confirmNoNeedQuantityClarify' or lastIntent == 'confirmNoWoQuantity':
                    confirmedItems.pop()
            confirmedItems.append(reservation)
            session_attributes['confirmedItems'] = json.dumps(confirmedItems)
            logger.debug('confirm_yes - if cost is yes, print session_attributes[confirmedItems] = {} '.format(session_attributes['confirmedItems']))

            confirmType = confirmItemType + item_type + confirmItemTypeAnythingElse

            session_attributes['lastIntent'] = intent_request['currentIntent']['name']
            # cofirm yes for charging, close the session.
            return close(
                session_attributes,
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': confirmType
                }
            )

    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        inputsentence = try_ex(lambda: intent_request['inputTranscript'])
        if inputsentence is not None:
            inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
            if inputsentenceHis is not None:
                inputsentenceHis = inputsentenceHis + "," + inputsentence
            else:
                inputsentenceHis = inputsentence

            session_attributes['inputsentenceHis'] = inputsentenceHis
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']

        '''
        if item_number:
            toDo = confirmYesToDo + item_number + ' ' + item_type + '. ' + anythingElse
        else:
            toDo = confirmYesToDo  + item_type +  '. ' + anythingElse
        '''
        session_attributes['lastIntent'] = intent_request['currentIntent']['name']
        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': anythingElse
            }
        )

#bath towels
#no I need 3 bath towels
def confirm_no_needQuantity(intent_request):
    item_type = try_ex(lambda: intent_request['currentIntent']['slots']['itemNeedQuantity'])
    item_number = try_ex(lambda: intent_request['currentIntent']['slots']['quantityList'])

    # To make sure item type is not None
    if item_type is None:
        logger.debug('confirm_no_needQuantity - Bot can not identify your intent/slot. Transfer to FrontDesk after trying for two times')
        return delegate(
            intent_request['sessionAttributes'],
            {}
        )

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    session_attributes['lastIntent'] = intent_request['currentIntent']['name']

    # the current reservation.
    reservation = {
        'itemNeedQuantity': item_type,
        'quantityList': item_number,
        'validationSet': ''
    }

    session_attributes['currentReservation'] = json.dumps(reservation)

    item_type_slot = 'itemNeedQuantity'
    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.

        # item type validation check
        validation_result = validate_item_type(item_type, item_type_slot, session_attributes)
        logger.debug('lambda func: validation_result: {}'.format(validation_result))
        reservation['validationSet'] = validation_result['validationSet'] # includes approvedQuest, checkingQuest
        session_attributes['currentReservation'] = json.dumps(reservation)
        logger.debug('confirm_no_needQuantity - dialogcodehook - currentReservation: {}'.format(session_attributes['currentReservation']))

        # validate haveNone,cost,in room,then close the session.
        if validation_result['message']['content']:
            # do not have case
            if not validation_result['isValid']:
                confirmedItems = []
                if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
                    confirmedItems = json.loads(session_attributes['confirmedItems'])
                    #delete last confirm item
                    confirmedItems.pop()
                    session_attributes['confirmedItems'] = json.dumps(confirmedItems)

            return close(intent_request['sessionAttributes'],
                               'Fulfilled',
                               validation_result['message'])

        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        return delegate(output_session_attributes, get_current_slots(intent_request))

    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        # Validate any slot has been specified to check if any invalid, re-elicit for its value
        if item_type is not None:
            toDo = confirmItemType + item_number + ' ' + item_type + ' ' + confirmItemTypeAnythingElse
        else:
            toDo = anythingElse

        inputsentence = try_ex(lambda: intent_request['inputTranscript'])
        if inputsentence is not None:
            inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
            if inputsentenceHis is not None:
                inputsentenceHis = inputsentenceHis + "," + inputsentence
            else:
                inputsentenceHis = inputsentence

            session_attributes['inputsentenceHis'] = inputsentenceHis
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']

        confirmedItems = []
        if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
            confirmedItems = json.loads(session_attributes['confirmedItems'])
            #delete last confirm item
            confirmedItems.pop()
        confirmedItems.append(reservation)
        session_attributes['confirmedItems'] = json.dumps(confirmedItems)

        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': toDo
            }
        )

#no I need 3
def confirmNoNeedQuantityClarify(intent_request):
    item_number = try_ex(lambda: intent_request['currentIntent']['slots']['quantityList'])
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    # To make sure item type is not None
    if item_number is None:
        logger.debug('confirmNoNeedQuantityClarify - Bot can not identify your intent/slot. Transfer to FrontDesk after trying for two times')
        return delegate(
            intent_request['sessionAttributes'],
            {}
        )

    # Get itemtype
    item_type = ''
    confirmedItems = []
    #logger.debug('confirmNoNeedQuantityClarify - intent_request={}:'.format(intent_request))
    logger.debug('confirmNoNeedQuantityClarify - session_attributes[confirmedItems]={}:'.format(session_attributes['confirmedItems']))
    if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
        confirmedItems = json.loads(session_attributes['confirmedItems'])
        lastconfirmItem = confirmedItems[-1]
        item_type = try_ex(lambda: lastconfirmItem['itemNeedQuantity'])
        #logger.debug('confirmNoNeedQuantityClarify -  lastconfirmItem is {} '.format(lastconfirmItem))
        logger.debug('confirmNoNeedQuantityClarify -  item_type is {} '.format(item_type))

    # the current reservation.
    reservation = {
        'itemNeedQuantity': item_type,
        'quantityList': item_number
    }

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    session_attributes['currentReservation'] = json.dumps(reservation)
    session_attributes['lastIntent'] = intent_request['currentIntent']['name']

    #no i need 9 , this senario doesn't need DialogCodeHook to do type validation
    #if intent_request['invocationSource'] == 'DialogCodeHook':

    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        if item_number is not None:
            toDo = confirmItemType + item_number + ' ' + item_type + ' ' + confirmItemTypeAnythingElse
        else:
            toDo = anythingElse

        inputsentence = try_ex(lambda: intent_request['inputTranscript'])
        if inputsentence is not None:
            inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
            if inputsentenceHis is not None:
                inputsentenceHis = inputsentenceHis + "," + inputsentence
            else:
                inputsentenceHis = inputsentence

            session_attributes['inputsentenceHis'] = inputsentenceHis
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']

        confirmedItems = []
        if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
            confirmedItems = json.loads(session_attributes['confirmedItems'])
            #delete last confirm item
            confirmedItems.pop()
        confirmedItems.append(reservation)
        session_attributes['confirmedItems'] = json.dumps(confirmedItems)

        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': toDo
            }
        )

#no I need hand towels
def confirmNoWoQuantity(intent_request):
    item_type = try_ex(lambda: intent_request['currentIntent']['slots']['itemNeedQuantity'])
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    # To make sure item type is not None
    if item_type is None:
        logger.debug('confirmNoWoQuantity - Bot can not identify your intent/slot. Transfer to FrontDesk after trying for two times')
        return delegate(
            intent_request['sessionAttributes'],
            {
            }
        )

    # Get item_number
    item_number = ''
    confirmedItems = []
    #logger.debug('confirmNoWoQuantity - intent_request={}:'.format(intent_request))
    logger.debug('confirmNoWoQuantity - session_attributes[confirmedItems]={}:'.format(session_attributes['confirmedItems']))
    if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
        confirmedItems = json.loads(session_attributes['confirmedItems'])
        lastconfirmItem = confirmedItems[-1]
        item_number = try_ex(lambda: lastconfirmItem['quantityList'])
        #logger.debug('confirmNoWoQuantity -  lastconfirmItem is {} '.format(lastconfirmItem))
        logger.debug('confirmNoWoQuantity -  item_type is {} '.format(item_number))

    # the current reservation.
    reservation = {
        'itemNeedQuantity': item_type,
        'quantityList': item_number,
        'validationSet': ''
    }

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    session_attributes['currentReservation'] = json.dumps(reservation)
    session_attributes['lastIntent'] = intent_request['currentIntent']['name']

    item_type_slot = 'itemNeedQuantity'
    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.

        # item type validation check
        validation_result = validate_item_type(item_type, item_type_slot, session_attributes)
        logger.debug('lambda func: validation_result: {}'.format(validation_result))
        reservation['validationSet'] = validation_result['validationSet'] # includes approvedQuest, checkingQuest
        session_attributes['currentReservation'] = json.dumps(reservation)
        logger.debug('request_item - dialogcodehook - currentReservation: {}'.format(session_attributes['currentReservation']))

        # validate haveNone,cost,in room,then close the session.
        if validation_result['message']['content']:
            # do not have case
            if not validation_result['isValid']:
                confirmedItems = []
                if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
                    confirmedItems = json.loads(session_attributes['confirmedItems'])
                    #delete last confirm item
                    confirmedItems.pop()
                    session_attributes['confirmedItems'] = json.dumps(confirmedItems)

            return close(intent_request['sessionAttributes'],
                               'Fulfilled',
                               validation_result['message'])

        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        return delegate(output_session_attributes, get_current_slots(intent_request))

    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        if item_type is not None:
            toDo = confirmItemType + item_number + ' ' + item_type + ' ' + confirmItemTypeAnythingElse
        else:
            toDo = anythingElse

        inputsentence = try_ex(lambda: intent_request['inputTranscript'])
        if inputsentence is not None:
            inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
            if inputsentenceHis is not None:
                inputsentenceHis = inputsentenceHis + "," + inputsentence
            else:
                inputsentenceHis = inputsentence

            session_attributes['inputsentenceHis'] = inputsentenceHis
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']

        confirmedItems = []
        if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
            confirmedItems = json.loads(session_attributes['confirmedItems'])
            #delete last confirm item
            confirmedItems.pop()
        confirmedItems.append(reservation)
        session_attributes['confirmedItems'] = json.dumps(confirmedItems)

        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': toDo
            }
        )

def confirm_no_only(intent_request):
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    lastIntent = try_ex(lambda: session_attributes['lastIntent'])

    logger.debug('confim_no_only session_attributes[currentReservation] = {}'.format(session_attributes['currentReservation']))

    checkingReservation = {}
    if try_ex(lambda: session_attributes['currentReservation']) is not None and try_ex(lambda: session_attributes['currentReservation']) != '':
        checkingReservation = json.loads(session_attributes['currentReservation'])
        logger.debug('confirm_no_only -  currentReservation is not None, checkingReservation {} '.format(checkingReservation))

    if lastIntent == 'requestItemQuantity':
        checkingSet = ''
        checkingContent = ''
        if checkingReservation:
            checkingSet = try_ex(lambda: checkingReservation['validationSet'])
            if checkingSet:
                checkingContent = try_ex(lambda: checkingSet['checkingQuest']) if try_ex(lambda: checkingSet['checkingQuest']) is not None else ''
            item_type = try_ex(lambda: checkingReservation['itemNeedQuantity'])
            item_number = try_ex(lambda: checkingReservation['quantityList'])
        if checkingContent == 'inRoom':
            validationSet = json.loads(session_attributes['currentReservation'])['validationSet']
            checkingReservation['validationSet'] = updateItemValidationSet(validationSet, 'inRoom', None) # clear inRoom check status, make inRoom approve status
            session_attributes['currentReservation'] = json.dumps(checkingReservation)
            # fake a ConfirmedItem for item not find inRoom
            reservation = {
                'itemNeedQuantity': item_type,
                'quantityList': '',
                'time': getTimeNow()
            }
            confirmedItems = []
            if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
                confirmedItems = json.loads(session_attributes['confirmedItems'])
                # delete last confirmedItems if last intent is change intents
                if lastIntent == 'confirmNoNeedQuantity' or lastIntent == 'confirmNoNeedQuantityClarify' or lastIntent == 'confirmNoWoQuantity' :
                    confirmedItems.pop()
            confirmedItems.append(reservation)
            session_attributes['confirmedItems'] = json.dumps(confirmedItems)
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']
            logger.debug('confirm_no_only - if inRoom is no, print session_attributes[confirmedItems] = {} '.format(session_attributes['confirmedItems']))

            return close(
                session_attributes,
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': 'I apologize for the inconvenience. We will bring to you right away. Anything else I can help you with?'
                }
            )
        elif checkingContent == 'cost':
            validationSet = json.loads(session_attributes['currentReservation'])['validationSet']
            checkingReservation['validationSet'] = updateItemValidationSet(validationSet, 'cost', None) # clear cost check status
            session_attributes['currentReservation'] = json.dumps(checkingReservation)

            confirmedItems = []
            if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
                confirmedItems = json.loads(session_attributes['confirmedItems'])
                # delete last confirmedItems if last intent is change intents
                if lastIntent == 'confirmNoNeedQuantity' or lastIntent == 'confirmNoNeedQuantityClarify' or lastIntent == 'confirmNoWoQuantity':
                    confirmedItems.pop()
                    session_attributes['confirmedItems'] = json.dumps(confirmedItems)
            logger.debug('confirm_no_only  - if cost is no, print session_attributes[confirmedItems] = {} '.format(session_attributes['confirmedItems']))
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']

            return close(
                session_attributes,
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': anythingElse
                }
            )

    inputsentence = try_ex(lambda: intent_request['inputTranscript'])
    if inputsentence is not None:
        inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
        if inputsentenceHis is not None:
            inputsentenceHis = inputsentenceHis + "," + inputsentence
        else:
            inputsentenceHis = inputsentence

        session_attributes['inputsentenceHis'] = inputsentenceHis
        session_attributes['lastIntent'] = intent_request['currentIntent']['name']

        logger.debug('confirm_no_only  - at the end , print session_attributes[confirmedItems] = {} '.format(session_attributes['confirmedItems']))

    confirm_msg = build_confirm_msg(session_attributes)
    if confirm_msg == 'No request yet':  #if session_attributes == {}
        confirm_msg = thankyou

    logger.debug("confirmnoonly - lastIntent: {}".format(lastIntent))
    if lastIntent == 'confirmNoOnly' or lastIntent == 'confirmYes':
        room = getRoomNum(session_attributes)
        fullcall_id, call_id = getCallID(intent_request)
        #order = buildFinalOrder(session_attributes, fullcall_id)
        #sendOrder(order, call_id, room, '5') # check how to get bot version?
        # TODO: need to clear item_type, item_number, session_attributes
        session_attributes.clear()
        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': confirm_msg
            }
        )

    room = getRoomNum(session_attributes)
    fullcall_id, call_id = getCallID(intent_request)
    #order = buildFinalOrder(session_attributes, fullcall_id)
    #sendOrder(order, call_id, room, '5') # check how to get bot version?
    # TODO: need to clear item_type, item_number, session_attributes
    session_attributes.clear()
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': confirm_msg
        }
    )

def noOtherNeeds(intent_request):

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    logger.debug('noOtherNeeds session_attributes={}'.format(session_attributes))

    '''
    confirmedItems = try_ex(lambda: session_attributes['confirmedItems'])
    inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
    if confirmedItems:
        email_subj = "[Guest Services] New Request  HK"
        sendmail(email_subj, confirmedItems+inputsentenceHis)
    '''

    inputsentence = try_ex(lambda: intent_request['inputTranscript'])
    if inputsentence is not None:
        inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
        if inputsentenceHis is not None:
            inputsentenceHis = inputsentenceHis + "," + inputsentence
        else:
            inputsentenceHis = inputsentence

        session_attributes['inputsentenceHis'] = inputsentenceHis
        session_attributes['lastIntent'] = intent_request['currentIntent']['name']

    #set None
    #session_attributes['confirmedItems'] = "{}"
    #session_attributes['inputsentenceHis'] = "{}"

    confirm_msg = build_confirm_msg(session_attributes)
    if confirm_msg == 'No request yet':  #if session_attributes == {}
        confirm_msg = thankyou

    room = getRoomNum(session_attributes)
    fullcall_id, call_id = getCallID(intent_request)
    #order = buildFinalOrder(session_attributes, fullcall_id)
    #sendOrder(order, call_id, room, '5') # check how to get bot version?
    # TODO: need to clear item_type, item_number, session_attributes
    session_attributes.clear()
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': confirm_msg
        }
    )

def confirmNo_requestMessageDeliver(intent_request):
    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        inputsentence = try_ex(lambda: intent_request['inputTranscript'])
        if inputsentence is not None:
            session_attributes['inputsentenceHis'] = updateInputSentenceHis(session_attributes, inputsentence)
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']
            logger.debug("requestMessageDeliver - session_attributes - before: {}".format(session_attributes))
            confirmedItems = removeLastConfirmedItem(session_attributes)
            session_attributes['confirmedItems'] = json.dumps(confirmedItems)
            logger.debug("requestMessageDeliver - session_attributes - middle: {}".format(session_attributes))
            slots = get_current_slots(intent_request)
            confirmInfo = getConfirmInfo(slots, inputsentence)
            logger.debug('confirmNo_requestMessageDeliver - confirmInfo: {}'.format(confirmInfo))
            confirmedItems = addConfirmedItem(session_attributes, confirmInfo['reservation'])
            logger.debug('confirmNo_requestMessageDeliver - confirmedItems: {}'.format(confirmedItems))
            session_attributes['confirmedItems'] = json.dumps(confirmedItems)
            logger.debug("requestMessageDeliver - session_attributes: {}".format(session_attributes))
            return close(
                session_attributes,
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': confirmInfo['returnMsg'] + confirmItemTypeAnythingElse
                }
            )
# --- Intents ---

def dispatch(intent_request):
    logger.debug('dispath intent_request: {}'.format(intent_request))
    """
    Called when the user specifies an intent for this bot.
    """
    if 'currentIntent' in intent_request:
        intent_name = intent_request['currentIntent']['name']
    # Dispatch to your bot's intent handlers
    if (intent_name == 'requestItemQuantity'):
        return request_item(intent_request)
    if (intent_name == 'requestRepairItems'):
        return requestRepairItems(intent_request)
    if (intent_name == 'requestReplaceItems'):
        return requestReplaceItems(intent_request)
    if (intent_name == 'requestInformation'):
        return requestInformation(intent_request)
    if (intent_name == 'requestMessageDeliver'):
        return requestMessageDeliver(intent_request)
    if (intent_name == 'requestCallBack'):
        return requestCallBack(intent_request)
    if (intent_name == 'confirmYes'):
        return confirm_yes(intent_request)
    if (intent_name == 'confirmNoNeedQuantity'):
        return confirm_no_needQuantity(intent_request)
    if (intent_name == 'confirmNoOnly'):
        return confirm_no_only(intent_request)
    if (intent_name == 'confirmNoNeedQuantityClarify'):
        return confirmNoNeedQuantityClarify(intent_request)
    if (intent_name == 'confirmNoWoQuantity'):
        return confirmNoWoQuantity(intent_request)
    if (intent_name == 'confirmNo_requestMessageDeliver'):
        return confirmNo_requestMessageDeliver(intent_request)
    if (intent_name == 'noOtherNeeds'):
        return noOtherNeeds(intent_request)
    if (intent_name == 'byebye'):
        return byebye(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')

# --- Main handler ---


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    #os.environ['TZ'] = 'EDT'
    time.tzset()
    logger.debug('event={}'.format(event))

    return dispatch(event)
