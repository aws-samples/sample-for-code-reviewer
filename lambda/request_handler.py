import traceback
import json, os, re, datetime, logging
import boto3, base
import codelib
from logger import init_logger

REQUEST_TABLE 				= os.getenv('REQUEST_TABLE')
TASK_DISPATCHER_FUN_NAME 	= os.getenv('TASK_DISPATCHER_FUN_NAME')
	
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
sqs_client = boto3.client('sqs')

init_logger()
log = logging.getLogger('crlog_{}'.format(__name__))

def __candel_parse_process_modes(event, context, repo_context, params):
	# TODO
	web_url = params.get('web_url')
	commit_id = params.get('commit_id')
	target_branch = params.get('target_branch')
	event_type = params.get('event_type')
	valid_modes = [ 'all', 'single', 'diff' ]

	rules = codelib.get_rules(repo_context, commit_id, target_branch)
	log.info('Get rules.', extra=dict(rules=rules))
	
	modes = []
	for rule in rules:
		if rule.get('branch') == target_branch and rule.get('event') == event_type:
			mode = rule.get('mode')
			mode = mode.lower() if mode else mode
			if mode in valid_modes and mode not in modes:
				modes.append(mode)
	log.info(f'Found code review modes for branch({target_branch}) and commit id({commit_id}): {modes}')
	return modes

def get_invoker(event):
	try:
		body = json.loads(event.get('body', '{}'))
		invoker = body.get('invoker')
		return invoker
	except Exception as ex:
		log.info('Fail to parse invoker in body.', extra=dict(exception=str(ex)))
		return None

def process(event, context):

	log.info(event, extra=dict(label='event'))
	current_time = datetime.datetime.now()
	
	try:

		invoker = get_invoker(event)

		# 解析Gitlab参数
		if invoker == 'webtool':
			params = codelib.parse_webtool_parameters(event)
		else:
			params = codelib.parse_parameters(event)

		log.info('Request identifier: {}'.format(params['request_id']))
		log.info('Project={project_id}({project_name}), Commit={commit_id}, Ref={ref}'.format(**params))
		log.info('Repository URL={repo_url}, Private Token={private_token}'.format(**params))
		log.info('Parameters are parsed.', extra=dict(params=params))
	
		repo_context = codelib.init_repo_context(params)

		# 格式化commit id
		previous_commit_id 	= params.get('previous_commit_id')
		cid = codelib.format_commit_id(repo_context, params.get('target_branch'), previous_commit_id)
		if previous_commit_id != cid:
			log.info(f'Set previous_commit_id from {previous_commit_id} to commit id({cid})')
			params['previous_commit_id'] = cid
		commit_id = params.get('commit_id')
		cid = codelib.format_commit_id(repo_context, params.get('target_branch'), commit_id)
		if commit_id != cid:
			log.info(f'Set commit_id from {commit_id} to commit id({cid})')
			params['commit_id'] = cid

		# 向数据库插入记录
		dynamodb.Table(REQUEST_TABLE).put_item(Item={
			'commit_id': params['commit_id'],
			'request_id': params['request_id'],
			'project_name': params.get('project_name', 'No Name Project'),
			'task_status': base.STATUS_START,
			'task_complete': 0,
			'task_failure': 0,
			'task_total': 0,
			'create_time': str(current_time),
			'update_time': str(current_time),
		})
		log.info('Complete inserting record to ddb.')
		
		# 调用第二个Lambda函数，使用'Event'进行异步调用
		payload = base.dump_json(params)
		lambda_client.invoke(FunctionName=TASK_DISPATCHER_FUN_NAME, InvocationType='Event', Payload=payload)
		log.info('Complete invoking task dispatcher.', extra=dict(payload=payload))

		log.info(f'Complete request handling for request({params["request_id"]}).')

		return base.response_success_post(dict(request_id=params['request_id'], commit_id=params['commit_id']))

	except base.CodelibException as ex:
		log.info('Occur codelib exception.', extra=dict(exception=str(ex)))
		return base.response_failure_post(ex.code)
	except Exception as ex:
		log.error(f'Fail to process webhook request.', extra=dict(exception=str(ex)))
		return base.response_failure_post(str(ex))

def lambda_handler(event, context):
	return process(event, context)
