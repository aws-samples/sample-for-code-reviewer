import os, boto3, base, json, logging
from logger import init_logger

REQUEST_TABLE 				= os.getenv('REQUEST_TABLE')
TASK_TABLE 					= os.getenv('TASK_TABLE')

dynamodb = boto3.resource('dynamodb')
s3 = boto3.resource("s3")

init_logger()
log = logging.getLogger('crlog_{}'.format(__name__))

def lambda_handler(event, context):
	
	log.info(event, extra=dict(label='event'))
	params = event.get('queryStringParameters', {})
	commit_id = params.get('commit_id')
	request_id = params.get('request_id')
	
	headers = {
		"Access-Control-Allow-Headers" : "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,x-gitlab-token",
		"Access-Control-Allow-Origin": "*",
		"Access-Control-Allow-Methods": "OPTIONS,GET"
	}
	
	try:
		
		item = dynamodb.Table(REQUEST_TABLE).get_item(Key=dict(commit_id=commit_id, request_id=request_id), ConsistentRead=True)
		result = item.get('Item')

		ready, url = False, None
		summary, tasks = None, []
		if result:
			summary = '{} tasks total: {} successful, {} failed。'.format(result.get('task_total'), result.get('task_complete'), result.get('task_failure'))
			if result.get('task_status') == 'Complete':
				ready = True
				url = result.get('report_url')
		log.info(f'Load ready: {ready}, report URL: {url}')

		# 获取所有Task
		items = dynamodb.Table(TASK_TABLE).query(
			KeyConditionExpression='request_id=:rid',
			ExpressionAttributeValues={ ':rid': request_id }
		)
		tasks = items.get('Items')

		bucket_name = os.getenv('BUCKET_NAME')
		for task in tasks:
			request_id, number, s3_key = map(task.get, ('request_id', 'number', 'data'))
			
			if s3_key:
				try:
					s3_content = base.get_s3_object(s3, bucket_name, s3_key)
					s3_data = json.loads(s3_content)
					task['bedrock_system'] = s3_data.get('prompt_system', '')
					task['bedrock_prompt'] = s3_data.get('prompt_user', '')
					task['bedrock_payload'] = s3_data.get('payload', '')
					task['result'] = s3_content
				except Exception as ex:
					log.info(f'Fail to parse data in s3({s3_key}) for task(request_id={request_id}, number={number})', extra=dict(exception=str(ex)))
					task['prompt_system'] = task['prompt_user'] = task['payload'] = task['result'] = ''

		ret = dict(succ=True, ready=ready, url=url, summary=summary, tasks=tasks)
		
		return { 'statusCode': 200, 'headers': headers, 'body': base.dump_json(ret) }

	except Exception as ex:
		log.error(f'Fail to process webhook request.', extra=dict(exception=str(ex)))
		return { 'statusCode': 200, 'headers': headers, 'body': base.dump_json(dict(succ=False, message=str(ex))) }
