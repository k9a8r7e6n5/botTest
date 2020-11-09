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
def get_slots(intent_request):
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
        if ele['itemNeedQuantity'] == itemType and ele['quantityListSpec'] == itemNum:
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
                "quantity": try_ex(lambda: ele['quantityListSpec']),
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
        logger.debug('sendOrder+++ {}'.format(sms_str))
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
        confirmMsg = 'You requested '
        confirmMsgEnd = 'is this correct?'
        confirmMsgBody = ''
        for ele in confirmedItems:
            itemType = try_ex(lambda: ele['itemNeedQuantity'])
            confirmMsgBody += ele['quantityListSpec'] + ' ' + itemType + ', '
            confirmAll = confirmMsg + confirmMsgBody + confirmMsgEnd
    logger.debug('confirm all the thing is: {}'.format(confirmAll))
    return confirmAll

""" --- Functions that control the bot's behavior --- """

def request_item(intent_request):
    """
    Performs dialog management and fulfillment for booking a hotel.
    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """

    intent_name = intent_request['currentIntent']['name']

    if intent_name == 'requestItemQuantity':
        # Get specific type
        item_type = try_ex(lambda: intent_request['currentIntent']['slots']['itemNeedQuantity'])
        item_number = try_ex(lambda: intent_request['currentIntent']['slots']['quantityList'])
        item_type_slot = 'itemNeedType'
        if item_type is None:
            # Get general item type
            item_type = try_ex(lambda: intent_request['currentIntent']['slots']['itemNeedType'])
            item_type_slot = 'itemNeedQuantity'
            # To make sure item type is not None
            if item_type is None:
                slots = get_slots(intent_request)
                return elicit_slot(intent_request['sessionAttributes'],
                    intent_request['currentIntent']['name'],
                    slots,
                    'itemNeedType',
                    {
                        'contentType': 'PlainText',
                        'content': NullItemType
                    }
                )

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    confirmation_status = intent_request['currentIntent']['confirmationStatus']

    reservation = {
        'itemNeedQuantity': item_type,
        'quantityListSpec': item_number,
        'validationSet': ''
    }

    session_attributes['currentReservation'] = json.dumps(reservation)

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        # confirm intent should ignore validation check
        validation_result = validate_item_type(item_type, item_type_slot, session_attributes)
        reservation['validationSet'] = validation_result['validationSet'] # includes approvedQuest, checkingQuest
        session_attributes['currentReservation'] = json.dumps(reservation)

        if validation_result['message']['content']:
            # need to enhance, not cover cost case
            # session_attributes['lastRoomItemReservation'] = reservation
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        return delegate(output_session_attributes, get_slots(intent_request))

    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        if ((intent_name == 'requestItemQuantity')):
            try_ex(lambda: session_attributes.pop('currentReservation'))
            session_attributes['lastConfirmedReservation'] = json.dumps(reservation)

        confirmType = confirmItemType + item_number + ' ' + item_type + ' ' + confirmItemTypeCorrect

        inputsentence = try_ex(lambda: intent_request['inputTranscript'])
        if inputsentence is not None:
            inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
            if inputsentenceHis is not None:
                inputsentenceHis = inputsentenceHis + "," + inputsentence
            else:
                inputsentenceHis = inputsentence

            session_attributes['inputsentenceHis'] = inputsentenceHis
            session_attributes['lastIntent'] = intent_request['currentIntent']['name']
        
        reservation = {
            'itemNeedQuantity': item_type,
            'quantityListSpec': item_number,
            'time': getTimeNow()
        }
        confirmedItems = []
        if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
            confirmedItems = json.loads(session_attributes['confirmedItems'])
        confirmedItems.append(reservation)
        session_attributes['confirmedItems'] = json.dumps(confirmedItems)
        #confirmType = 'You need ' + item_number + ' ' + item_type + '. Anything else?'

        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': anythingElse
            }
        )

def byebye(intent_request):
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    if session_attributes != {}:
        room = getRoomNum(session_attributes)
        fullcall_id, call_id = getCallID(intent_request)
        order = buildFinalOrder(session_attributes, fullcall_id)
        sendOrder(order, call_id, room, '5') # check how to get bot version?
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

    # add for flow #3
    checkingReservation = {}
    if try_ex(lambda: json.loads(session_attributes['currentReservation'])) is not None:
        checkingReservation = json.loads(session_attributes['currentReservation'])
    elif try_ex(lambda: json.loads(session_attributes['lastConfirmedReservation'])) is not None:
        checkingReservation = json.loads(session_attributes['lastConfirmedReservation'])

    checkingSet = ''
    checkingContent = ''
    if checkingReservation:
        checkingSet = try_ex(lambda: checkingReservation['validationSet'])
        if checkingSet:
            checkingContent = try_ex(lambda: checkingSet['checkingQuest']) if try_ex(lambda: checkingSet['checkingQuest']) is not None else ''
        item_type = try_ex(lambda: checkingReservation['itemNeedQuantity'])
        item_number = try_ex(lambda: checkingReservation['quantityListSpec'])

    if item_type is None or item_number is None:
        logger.error('Cannot receive item type or number!')
    if checkingContent == 'inRoom':
        validationSet = json.loads(session_attributes['currentReservation'])['validationSet']
        checkingReservation['validationSet'] = updateItemValidationSet(validationSet, 'inRoom', None) # clear inRoom check status, make inRoom approve status
        session_attributes['currentReservation'] = json.dumps(checkingReservation)
        session_attributes['lastIntent'] = intent_request['currentIntent']['name']

        # cofirm yes for item in the room, close the session.
        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': 'Anything else I can help you with today?'
            }
        )

    reservation = {
        'itemNeedQuantity': item_type,
        'quantityListSpec': item_number,
        'time': getTimeNow()
    }

    lastIntent = try_ex(lambda: session_attributes['lastIntent'])

    inputsentence = try_ex(lambda: intent_request['inputTranscript'])
    if inputsentence is not None:
        inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
        if inputsentenceHis is not None:
            inputsentenceHis = inputsentenceHis + "," + inputsentence
        else:
            inputsentenceHis = inputsentence

        session_attributes['inputsentenceHis'] = inputsentenceHis
        session_attributes['lastIntent'] = intent_request['currentIntent']['name']
    
    if lastIntent == 'confirmNoOnly':
        
        byebye(intent_request)
        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': "Thank you! We will bring your request to your room shortly. Enjoy your day!"
            }
        )

    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Have a nice day'
        }
    )


#bath towels
#no I need 3 bath towels
def confirm_no_needQuantity(intent_request):
    item_type = try_ex(lambda: intent_request['currentIntent']['slots']['itemNeedQuantity'])
    item_number = try_ex(lambda: intent_request['currentIntent']['slots']['quantityListSpec'])

    if item_type is None:
        return elicit_slot(intent_request['sessionAttributes'],
            intent_request['currentIntent']['name'],
            intent_request['currentIntent']['slots'],
            'itemNeedQuantity',
            {
                'contentType': 'PlainText',
                'content': NullItemType
            }
        )

    confirmation_status = intent_request['currentIntent']['confirmationStatus']
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    last_confirmed_reservation = try_ex(lambda: session_attributes['lastConfirmedReservation'])
    if last_confirmed_reservation:
        last_confirmed_reservation = json.loads(last_confirmed_reservation)
    confirmation_context = try_ex(lambda: session_attributes['confirmationContext'])

    item_typeold = try_ex(lambda: last_confirmed_reservation['itemNeedQuantity'])
    item_numberold = try_ex(lambda: last_confirmed_reservation['quantityListSpec'])

    #no I need bath towels

    # Load confirmation history and track the current reservation.
    reservation = {
        'itemNeedQuantityOld': item_typeold,
        'quantityListSpecOld': item_numberold,
        'itemNeedQuantity': item_type,
        'quantityListSpec': item_number
    }

    session_attributes['currentReservation'] = json.dumps(reservation)

    item_type_slot = 'itemNeedQuantity'
    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)
    
        # confirm intent should ignore validation check
        validation_result = validate_item_type(item_type, item_type_slot, session_attributes)
        reservation['validationSet'] = validation_result['validationSet'] # includes approvedQuest, checkingQuest
        session_attributes['currentReservation'] = json.dumps(reservation)
    
        if validation_result['message']['content']:
            # need to enhance, not cover cost case
            # session_attributes['lastRoomItemReservation'] = reservation
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        return delegate(output_session_attributes, get_slots(intent_request))

    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        # Validate any slot has been specified to check if any invalid, re-elicit for its value
        del session_attributes['currentReservation']
        session_attributes['lastConfirmedReservation'] = json.dumps(reservation)

        if item_type is not None:
            toDo = confirmItemType + item_number + ' ' + item_type + ' ' + confirmItemTypeCorrect
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
    item_number = try_ex(lambda: intent_request['currentIntent']['slots']['quantityListSpec'])
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    last_confirmed_reservation = try_ex(lambda: session_attributes['lastConfirmedReservation'])
    if last_confirmed_reservation:
        last_confirmed_reservation = json.loads(last_confirmed_reservation)
    confirmation_context = try_ex(lambda: session_attributes['confirmationContext'])

    item_typeold = try_ex(lambda: last_confirmed_reservation['itemNeedQuantity'])
    item_numberold = try_ex(lambda: last_confirmed_reservation['quantityListSpec'])

    #no I need 9
    item_type = item_typeold

    # Load confirmation history and track the current reservation.
    reservation = {
        'itemNeedQuantityOld': item_typeold,
        'quantityListSpecOld': item_numberold,
        'itemNeedQuantity': item_type,
        'quantityListSpec': item_number
    }

    session_attributes['currentReservation'] = json.dumps(reservation)

    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        del session_attributes['currentReservation']
        session_attributes['lastConfirmedReservation'] = json.dumps(reservation)

        if item_number is not None:
            toDo = confirmItemType + item_number + ' ' + item_type + ' ' + confirmItemTypeCorrect
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

    if item_type is None:
        return elicit_slot(intent_request['sessionAttributes'],
            intent_request['currentIntent']['name'],
            intent_request['currentIntent']['slots'],
            'itemNeedQuantity',
            {
                'contentType': 'PlainText',
                'content': NullItemType
            }
        )

    last_confirmed_reservation = try_ex(lambda: session_attributes['lastConfirmedReservation'])
    if last_confirmed_reservation:
        last_confirmed_reservation = json.loads(last_confirmed_reservation)
    confirmation_context = try_ex(lambda: session_attributes['confirmationContext'])

    item_typeold = try_ex(lambda: last_confirmed_reservation['itemNeedQuantity'])
    item_numberold = try_ex(lambda: last_confirmed_reservation['quantityListSpec'])

    #no I need hand towels
    item_number = item_numberold

    # Load confirmation history and track the current reservation.
    reservation = {
        'itemNeedQuantityOld': item_typeold,
        'quantityListSpecOld': item_numberold,
        'itemNeedQuantity': item_type,
        'quantityListSpec': item_number
    }

    session_attributes['currentReservation'] = json.dumps(reservation)

    item_type_slot = 'itemNeedQuantity'
    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)
    
        # confirm intent should ignore validation check
        validation_result = validate_item_type(item_type, item_type_slot, session_attributes)
        reservation['validationSet'] = validation_result['validationSet'] # includes approvedQuest, checkingQuest
        session_attributes['currentReservation'] = json.dumps(reservation)
    
        if validation_result['message']['content']:
            # need to enhance, not cover cost case
            # session_attributes['lastRoomItemReservation'] = reservation
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

    if intent_request['invocationSource'] == 'FulfillmentCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        del session_attributes['currentReservation']
        session_attributes['lastConfirmedReservation'] = json.dumps(reservation)

        if item_type is not None:
            toDo = confirmItemType + item_number + ' ' + item_type + ' ' + confirmItemTypeCorrect
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
    checkingReservation = {}
    if try_ex(lambda: json.loads(session_attributes['currentReservation'])) is not None:
        checkingReservation = json.loads(session_attributes['currentReservation'])
    elif try_ex(lambda: json.loads(session_attributes['lastConfirmedReservation'])) is not None:
        checkingReservation = json.loads(session_attributes['lastConfirmedReservation'])

    checkingSet = ''
    checkingContent = ''
    if checkingReservation:
        checkingSet = try_ex(lambda: checkingReservation['validationSet'])
        if checkingSet:
            checkingContent = try_ex(lambda: checkingSet['checkingQuest']) if try_ex(lambda: checkingSet['checkingQuest']) is not None else ''
        item_type = try_ex(lambda: checkingReservation['itemNeedQuantity'])
        item_number = try_ex(lambda: checkingReservation['quantityListSpec'])
    if checkingContent == 'inRoom':
        validationSet = json.loads(session_attributes['currentReservation'])['validationSet']
        checkingReservation['validationSet'] = updateItemValidationSet(validationSet, 'inRoom', None) # clear inRoom check status, make inRoom approve status
        session_attributes['currentReservation'] = json.dumps(checkingReservation)
        # fake a ConfirmedItem for item not find inRoom
        reservation = {
            'itemNeedQuantity': item_type,
            'quantityListSpec': '1',
            'time': getTimeNow()
        }
        confirmedItems = []
        if 'confirmedItems' in session_attributes and try_ex(lambda: session_attributes['confirmedItems']) != '':
            confirmedItems = json.loads(session_attributes['confirmedItems'])
        confirmedItems.append(reservation)
        session_attributes['confirmedItems'] = json.dumps(confirmedItems)
        
        session_attributes['lastIntent'] = intent_request['currentIntent']['name']

        return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': 'I apologize for the inconvenience. We will bring to you right away. Anything else I can help you with today?'
            }
        )

    lastIntent = try_ex(lambda: session_attributes['lastIntent'])

    inputsentence = try_ex(lambda: intent_request['inputTranscript'])
    if inputsentence is not None:
        inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
        if inputsentenceHis is not None:
            inputsentenceHis = inputsentenceHis + "," + inputsentence
        else:
            inputsentenceHis = inputsentence

        session_attributes['inputsentenceHis'] = inputsentenceHis
        session_attributes['lastIntent'] = intent_request['currentIntent']['name']
    
    confirm_msg = build_confirm_msg(session_attributes)
    if confirm_msg == 'No request yet':
        confirm_msg = 'Have a nice day, bye bye'

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

    confirmedItems = try_ex(lambda: session_attributes['confirmedItems'])
    inputsentenceHis = try_ex(lambda: session_attributes['inputsentenceHis'])
    if confirmedItems:
        email_subj = "[Guest Services] New Request  HK"
        sendmail(email_subj, confirmedItems+inputsentenceHis)

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
    session_attributes['confirmedItems'] = "{}"
    session_attributes['inputsentenceHis'] = "{}"

    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': "Happy to help!"
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
