import boto3
import os, datetime, logging
import base, task_base
from logger import init_logger

REQUEST_TABLE 			= os.getenv('REQUEST_TABLE')
TASK_TABLE 				= os.getenv('TASK_TABLE')
SNS_TOPIC_ARN 			= os.getenv('SNS_TOPIC_ARN')
REPORT_TIMEOUT_SECONDS 	= base.str_to_int(os.getenv('REPORT_TIMEOUT_SECONDS', '900'))

dynamodb 				= boto3.resource("dynamodb")
sns 					= boto3.resource('sns')
s3 						= boto3.resource("s3")

init_logger()
log = logging.getLogge('crlog_{}'.format(__name__))

def lambda_handler(event, context):

	log.info(event, extra=dict(label='event'))

	items = []
	hours = 24
	start_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
	result = dynamodb.Table(REQUEST_TABLE).query(
		IndexName='TaskStatusIndex',
		KeyConditionExpression='task_status = :s AND create_time >= :t',
		ExpressionAttributeValues={ ':s': base.STATUS_PROCESSING ,':t': str(start_time) },
		ConsistentRead=True
	)
	items = items + result.get('Items')
	result = dynamodb.Table(REQUEST_TABLE).query(
		IndexName='TaskStatusIndex',
		KeyConditionExpression='task_status = :s AND create_time >= :t',
		ExpressionAttributeValues={ ':s': base.STATUS_START ,':t': str(start_time) },
		ConsistentRead=True
	)
	items = items + result.get('Items')
	log.info(f'Load incomplete request record for the last {hours} hours.', extra=dict(items=items))

	for item in items:
		try:
			if item:
				task_base.check_request_progress(item, log)
		except Exception as ex:
			log.error('Fail to process request record.', extra=dict(exception=str(ex)))
	
	log.info('Complete cron function.')
