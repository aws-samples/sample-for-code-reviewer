import boto3
import traceback
import os, re, ast, json, time, datetime, logging, random
import base, task_base
from logger import init_logger

REQUEST_TABLE 			= os.getenv('REQUEST_TABLE')
TASK_SQS_URL 			= os.getenv('TASK_SQS_URL')
SNS_TOPIC_ARN 			= os.getenv('SNS_TOPIC_ARN')
SQS_MAX_DELAY 			= base.str_to_int(os.getenv('SQS_MAX_DELAY', '300'))   		# 最大延迟时间(秒)
SQS_BASE_DELAY 			= base.str_to_int(os.getenv('SQS_BASE_DELAY', '60'))   		# 初始延迟时间(秒)
SQS_MAX_RETRIES 		= base.str_to_int(os.getenv('SQS_MAX_RETRIES', '5'))		# 最大重试次数
MAX_FAILED_TIMES 		= base.str_to_int(os.getenv('MAX_FAILED_TIMES', '6'))
MAX_TOKEN_TO_SAMPLE 	= base.str_to_int(os.getenv('MAX_TOKEN_TO_SAMPLE', '10000'))
REPORT_TIMEOUT_SECONDS 	= base.str_to_int(os.getenv('REPORT_TIMEOUT_SECONDS', '900'))
TOP_P 					= base.str_to_float(os.getenv('TOP_P', '1'))
TEMPERATURE 			= base.str_to_float(os.getenv('TEMPERATURE', '0'))

BEDROCK_ACCESS_KEY 		= os.getenv('BEDROCK_ACCESS_KEY')
BEDROCK_SECRET_KEY 		= os.getenv('BEDROCK_SECRET_KEY')
BEDROCK_REGION 			= os.getenv('BEDROCK_REGION')

sqs						= boto3.client("sqs")
dynamodb				= boto3.resource("dynamodb")
sns						= boto3.resource('sns')
s3						= boto3.resource("s3")
if BEDROCK_ACCESS_KEY and BEDROCK_SECRET_KEY and BEDROCK_REGION:
	bedrock	= boto3.client(service_name="bedrock-runtime", aws_access_key_id=BEDROCK_ACCESS_KEY, aws_secret_access_key=BEDROCK_SECRET_KEY, region_name=BEDROCK_REGION)
else:
	bedrock	= boto3.client(service_name="bedrock-runtime")

init_logger()
log = logging.getLogger('crlog_{}'.format(__name__))

def invoke_claude3(model, prompt_data, task_name):

	params = dict(
		max_tokens = MAX_TOKEN_TO_SAMPLE,
		temperature = TEMPERATURE,
		top_p = TOP_P,
		anthropic_version= 'bedrock-2023-05-31',
	)
	
	if prompt_data.get('system'):
		params['system'] = prompt_data.get('system')
	
	params['messages'] = []
	messages = prompt_data.get('messages', '')
	if isinstance(messages, list):
		for i, message in enumerate(messages):
			role = 'user' if i % 2 == 0 else 'assistant'
			params['messages'].append({
				'role': role,
				'content': [{'type': 'text', 'text': message}]
			})
		prompt_user = 'It is multi round prompt, you can only use payload to invoke.'
	else:
		params['messages'].append({
			'role': 'user',
			'content': [{'type': 'text', 'text': prompt_user}]
		})
	
	if model == 'claude3.5-sonnet':
		llm_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
	elif model == 'claude3-opus':
		llm_id = 'anthropic.claude-3-opus-20240229-v1:0'
	elif model == 'claude3-sonnet':
		llm_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
	elif model == 'claude3-haiku':
		llm_id = 'anthropic.claude-3-haiku-20240307-v1:0'
	elif model == 'claude3': # 默认使用Sonnet
		llm_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
	else:
		raise Exception(f'Invalid claude3 model {model}')
		

	try:
		log.info(f'Bedrock - Invoking claude3 for {task_name}.', extra=dict(params=params))
		start_time = time.time()
		log.info(f'invoke model', extra=dict(payload=params, modelId=llm_id))
		response = bedrock.invoke_model(body=base.dump_json(params), modelId=llm_id)
		end_time = time.time()
		timecost = int(end_time * 1000 - start_time * 1000)
		start_time = datetime.datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
		end_time = datetime.datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
		response_body = json.loads(response.get('body').read())
		reply = response_body.get('content')[0]
		log.info(f'Bedrock - Claude3 replied for {task_name}.', extra=dict(reply=reply))
		ret = dict(
			model=llm_id,
			prompt_system=prompt_data.get('prompt_system'),
			prompt_user=prompt_user,
			text=reply['text'],
			payload=base.dump_json(params),
			timecost=timecost,
			start_time=start_time,
			end_time=end_time
		)
		return ret
	except Exception as ex:
		raise Exception(f'Fail to invoke Claude3: {ex}') from ex

def invoke_bedrock(task_name, prompt_data):
	"""
	Assume prompt_data has valid field: current_retry, max_retry, messages, model
	"""
	model = prompt_data.get('model')
	while prompt_data['current_retry'] < prompt_data['max_retry']:

		try:

			if model in ['claude3', 'claude3-haiku', 'claude3-sonnet', 'claude3-opus', 'claude3.5-sonnet']:

				reply = invoke_claude3(model, prompt_data, task_name)

				prompt_data['messages'].append(reply['text'])
				prompt_data['latest_reply'] = reply['text']
				prompt_data['payload'] = reply['payload']
				prompt_data['end_time'] = reply['end_time']
				if 'start_time' not in prompt_data:
					prompt_data['start_time'] = reply['start_time']
				if 'timecost' not in prompt_data:
					prompt_data['timecost'] = reply['timecost']
				else:
					prompt_data['timecost'] += reply['timecost']

			else:
				log.info(f'Mode({model}) is not support.')
				reply = dict()
			
			return prompt_data

		except Exception as ex:

			prompt_data['current_retry'] += 1
			expo = 2 ** (prompt_data['current_retry'] - 1)
			seed = random.randint(-SQS_BASE_DELAY, SQS_BASE_DELAY)
			delay = min(SQS_BASE_DELAY * expo + seed, SQS_MAX_DELAY)
			log.info(f'Fail to process SQS record for the {prompt_data["current_retry"]} times.', extra=dict(exception=str(ex)))
			
			if not isinstance(prompt_data.get('error_messages'), list):
				prompt_data['error_messages'] = list()
			prompt_data['error_messages'].append(dict(err=str(ex), traceback=traceback.format_exc()))

			commit_id, request_id, number, mode = base.extract_dict(prompt_data.get('context', {}), 'commit_id, request_id, number, mode')
			update_failure_task(
				commit_id, request_id, number, mode, 
				base.dump_json(prompt_data['error_messages']), 
				prompt_data.get('system'), 
				base.dump_json(prompt_data.get('messages')), 
				True
			)
			
			log.info(f"Retrying in {delay} seconds...")
			time.sleep(delay)  # 延迟一段时间后重试
	
	# 跳出循环即表示重试多次失败
	commit_id, request_id, number, mode = base.extract_dict(prompt_data.get('context', {}), 'commit_id, request_id, number, mode')
	update_failure_task(
		commit_id, request_id, number, mode, 
		base.dump_json(prompt_data['error_messages']), 
		prompt_data.get('system'), 
		base.dump_json(prompt_data.get('messages')), 
		False
	)
	log.info(f'Review failure is saved in {task_name}.')
	raise Exception(f'Fail to process {task_name} for {prompt_data["max_retry"]} times')


def extract_bedrock_response(text):
	
	match = re.search(r'<output>(.*?)</output>', text, re.DOTALL)
	if not match:
		log.info('No <output> tag found in response.', extra=dict(text=text))
		content = ''
	else:
		content = match.group(1)

	try:
		log.info('Try to parse json result.', extra=dict(content=content))
		python_object = ast.literal_eval(content)
		
		if isinstance(python_object, dict):
			python_object = [python_object]
		elif not isinstance(python_object, list):
			raise ValueError("Content is not a list or dict")
	except Exception as ex:
		log.info('Fail to parse JSON content.', extra=dict(content=content, exception=str(ex)))
		raise base.CRError(1, f'Fail to parse JSON content from: {content}') from ex

	return python_object

def invoke_and_extract_bedrock(task_name, prompt_data, message):

	if not isinstance(prompt_data.get('current_retry'), int):
		raise Exception(f'current_retry({prompt_data.get("current_retry")}) in prompt_data is not int.')
	if not isinstance(prompt_data.get('max_retry'), int):
		raise Exception(f'max_retry({prompt_data.get("max_retry")}) in prompt_data is not int.')
	
	prompt_data['messages'].append(message)
	prompt_data = invoke_bedrock(task_name, prompt_data)
	reply = prompt_data.get('latest_reply')
	log.info(f'Get bedrock result.', extra=dict(reply=reply))
	try:
		content = extract_bedrock_response(reply)
		prompt_data['content'] = content
	except Exception as ex:
		log.info('Fail to parse JSON in output tag. Try to rectify the JSON output.', extra=dict(text=reply))
		prompt_data['current_retry'] += 1
		if prompt_data['current_retry'] < prompt_data['max_retry']:
			JSON_RECTIFIER_PROMPT = 'The JSON in <output> tag seems invalid, it can not be convert into JSON object in Python. Please check and re-output again. Output all your message in this format \"<output>your finding</output><thought>your thought</thought>\".\nIMPORTANT:\n  - nothing should be output outside <output> and <thought> tag.'
			prompt_data = invoke_and_extract_bedrock(task_name, prompt_data, JSON_RECTIFIER_PROMPT)
	
	return prompt_data

def handle_code_review(record, event, context):

	log.info(event, extra=dict(label='task event'))
	log.info(context, extra=dict(label='task context'))

	request_id = event.get('request_id')
	number = event.get('number')
	label = f'task(request_id={request_id}, number={number})'
	log.info(f'Try to do code review for {label}...')

	# 校验SQS Event必要字段
	validate_sqs_event(event)
	commit_id, request_id, number, mode, model, prompt_system, prompt_user, confirm_prompt, rule_name = base.extract_dict(event, 'commit_id, request_id, number, mode, model, prompt_system, prompt_user, confirm_prompt, rule_name')
	current_timestamp = datetime.datetime.now()
	model = model.lower()
	
	try:
		create_task(commit_id, request_id, number, mode, model)
	except Exception as ex:
		raise Exception(f'Fail to create task: {ex}') from ex

	prompt_data = dict(
		context = dict(commit_id = commit_id, request_id = request_id, number = number, mode = mode),
		model=model, 
		system=prompt_system, 
		messages=[], 
		current_retry=0, 
		max_retry=SQS_MAX_RETRIES
	)

	prompt_data = invoke_and_extract_bedrock(label, prompt_data, prompt_user)
	
	if confirm_prompt:
		log.info('Try to confirm last output.')
		prompt_data = invoke_and_extract_bedrock(label, prompt_data, confirm_prompt)
	
	result = dict(
		commit_id = commit_id,
		request_id = request_id,
		rule = rule_name,
		model = model,
		content = prompt_data.get('content', ''),
		timestamp = str(current_timestamp),
		start_time = prompt_data.get('start_time', ''),
		end_time = prompt_data.get('end_time', ''),
		timecost = prompt_data.get('timecost', ''),
		payload = prompt_data.get('payload', ''),
		prompt_system = prompt_data.get('system', ''),
		prompt_user = base.dump_json(prompt_data.get('messages')[::2])
	)

	update_complete_task(commit_id, request_id, number, mode, result)
	task_base.check_request_progress_by_pksk(commit_id, request_id, log)
	log.info(f'Review result is saved in {label}', extra=dict(label=label, result=result))
	return 
		

def create_task(commit_id, request_id, number, mode, model):
	try:
		datetime_str = str(datetime.datetime.now())
		table_name = os.getenv('TASK_TABLE')
		dynamodb.Table(table_name).put_item(Item={
			'request_id': request_id,
			'number': number,
			'mode': mode,
			'model': model,
			'retry_times': 0, 
			'create_time': datetime_str,
			'update_time': datetime_str,
		})
	except Exception as e:
		raise Exception (f'Fail to create TASK for commit_id({commit_id}) and mode({mode}).') from e
	
def update_complete_task(commit_id, request_id, number, mode, result):
	try:

		# 保存数据到S3
		s3_data = result
		bucket_name = os.getenv('BUCKET_NAME')
		s3_key = f"result/{request_id}/{number}.json"
		base.put_s3_object(s3, bucket_name, s3_key, base.dump_json(s3_data), 'Content-Type: application/json')
		
		datetime_str = str(datetime.datetime.now())
		table_name = os.getenv('TASK_TABLE')
		dynamodb.Table(table_name).update_item(
			Key={'request_id': request_id, 'number': number},
			UpdateExpression='set succ = :s, update_time = :t, bedrock_model = :bm, bedrock_start_time = :bst, bedrock_end_time = :bet, bedrock_timecost = :btc, #d = :d',
			ExpressionAttributeNames={
				'#d': 'data'
			},
			ExpressionAttributeValues={
				':s': True,
				':t': datetime_str,
				':bm': result.get('model'),
				':bst': result.get('start_time'),
				':bet': result.get('end_time'),
				':btc': result.get('timecost'),
				':d': s3_key
			},
			ReturnValues='ALL_NEW'
		)
		# 更新Request表
		dynamodb.Table(REQUEST_TABLE).update_item(
			Key = { 'commit_id': commit_id, 'request_id': request_id },
			UpdateExpression = 'set task_status = :s, task_complete = task_complete + :tc, update_time = :t',
			ExpressionAttributeValues = { ':s': base.STATUS_PROCESSING, ':tc': 1, ':t': datetime_str },
			ReturnValues = 'ALL_NEW'
		)
	except Exception as e:
		raise Exception (f'Fail to update TASK COMPLETE for commit_id({commit_id}) and mode({mode}).') from e
	
def update_failure_task(commit_id, request_id, number, mode, error_message, prompt_system, prompt_user, need_retry=False):
	try:
		datetime_str = str(datetime.datetime.now())
		table_name = os.getenv('TASK_TABLE')
		dynamodb.Table(table_name).update_item(
			Key = { 'request_id': request_id, 'number': number },
			UpdateExpression = 'set retry_times = retry_times + :rt, succ = :s, message = :m, update_time = :t, bedrock_system = :bsp, bedrock_prompt = :bup',
			ExpressionAttributeValues = { 
				':rt': 1,
				':s': False, 
				':m': error_message,
				':t': datetime_str,
				':bsp': prompt_system,
				':bup': prompt_user
			},
			ReturnValues = 'ALL_NEW'
		)
		if not need_retry:
			dynamodb.Table(REQUEST_TABLE).update_item(
				Key = { 'commit_id': commit_id, 'request_id': request_id },
				UpdateExpression = 'set task_status = :s, task_failure = task_failure + :tf, update_time = :t',
				ExpressionAttributeValues = { ':s': base.STATUS_PROCESSING, ':tf': 1, ':t': datetime_str },
				ReturnValues = 'ALL_NEW'
			)
	except Exception as ex:
		log.info(f'Fail to update TASK FAILURE for commit_id({commit_id}) and mode({mode}).', extra=dict(exception=str(ex)))

def validate_sqs_event(event):
	required = [ 'context', 'commit_id', 'mode', 'model', 'rule_name', 'prompt_user', 'prompt_system' ]
	for field in required:
		if field not in event:
			raise Exception(f'SQS event does not have field {field} - {event}')
	return True

def lambda_handler(event, context):

	log.info(event, extra=dict(label='event'))
	log.info('Receiving {} SQS records'.format(len(event["Records"])))

	batch_item_failures, batch_item_successes = [], []
	for record in event["Records"]:
		
		log.info('Processing SQS record.', extra=dict(record=record))

		base64_text = record["body"]
		body_text = base.decode_base64(base64_text)
		log.info(body_text, extra=dict(label='plain body'))
		
		sqs_event = json.loads(body_text)
		sqs_context = sqs_event.get('context', {})
	
		try:
			handle_code_review(record, sqs_event, sqs_context)
			batch_item_successes.append({"itemIdentifier": record['messageId']})
		except Exception as ex:
			log.info(f'Fail to check code review result.', extra=dict(exception=str(ex)))
			batch_item_failures.append({"itemIdentifier": record['messageId']})

	batch_response = dict(batchItemSeccesses = batch_item_successes, batchItemFailures = batch_item_failures)
	log.info(f'SQS process results: {batch_response}')
	return batch_response
