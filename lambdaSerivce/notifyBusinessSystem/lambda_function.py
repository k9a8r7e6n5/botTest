import json
import logging
import boto3

from botocore.exceptions import ClientError

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
# Create a new client and specify a region.
clientPinpoint = boto3.client('pinpoint',region_name=region)
clientConnect = boto3.client('connect',region_name=region)
clientlex = boto3.client('lex-runtime',region_name=region)


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

def notifyTransferFailure(contactId):
    subj = "Call Transfer Failed!"
    body_html = "[Guest Serivces] Contact ID " + contactId + " asked to speak to Front Desk but failed. Please call back!"
    sendmail(subj, body_html)

def dispatch(callDetails):
    # need confirmedItems?
    contact_id = callDetails['Details']['ContactData']['Attributes']['contact_id']
    notifyTransferFailure(contact_id)

def lambda_handler(event, context):
    # TODO implement
    logger.debug('notifyBusinessSystem event={}'.format(event))
    dispatch(event)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from notifyBusinessSystem_Lambda!')
    }
