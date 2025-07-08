import boto3
import os, re, datetime, logging
import base, codelib, report
from logger import init_logger

# Initialize AWS services clients
dynamodb 				= boto3.resource("dynamodb")
sqs_client 				= boto3.client("sqs")
sns						= boto3.resource('sns')
s3						= boto3.resource("s3")

init_logger()
log = logging.getLogger('crlog_{}'.format(__name__))

def match_branch(pattern, branch):
	return pattern == branch

def send_message(data):
	sqs_url = os.getenv('TASK_SQS_URL')
	try:
		log.info(f'Prepare to send message to SQS({sqs_url}).', extra=dict(sqs_message=data))
		message = base.encode_base64(base.dump_json(data))
		response = sqs_client.send_message(QueueUrl=sqs_url, MessageBody=message)
		log.info(f'Succeed to send message to SQS({sqs_url}) in base64.', extra=dict(sqs_message_base64=message))
		return True
	except Exception as ex:
		log.error(f'Fail to send message to SQS({sqs_url}).', extra=dict(exception=str(ex)))
		return False

def format_prompt(pattern, variables, code=None):
	text = pattern
	if variables:
		for key in variables:
			string = str(variables.get(key, ''))
			text = text.replace('{{' + key + '}}', string.strip())
	if code: 
		text = text.replace('{{code}}', code)
	return text

def get_prompt_data(mode, rule, code, variables=None):
	
	if rule.get('mode') != mode: return None
	
	model = rule.get('model') or ''
	if model.startswith('claude3'):
		if rule.get('prompt_user'):
			prompt_system = rule.get('prompt_system')
			prompt_user = rule.get('prompt_user')
		else:
			prompt_system = rule.get('system', '')
			field_excludes = ['name', 'event', 'mode', 'model', 'branch', 'target', 'system', 'order', 'confirm']
			
			# 获取 order，如果不存在则设为空列表
			order = rule.get('order', [])
			
			# 创建一个包含所有非排除字段的列表
			all_fields = [key for key in rule.keys() if key.lower() not in field_excludes]
			
			# 按照 order 中的顺序排序字段，未在 order 中的字段保持原顺序
			sorted_fields = sorted(all_fields, key=lambda x: order.index(x) if x in order else len(order))
			
			# 构建 prompt_user
			prompt_user = ''
			for key in sorted_fields:
				value = rule.get(key)
				prompt_user = f'{prompt_user}\n\n{value}' if prompt_user else value
			
			prompt_user = f'以下是我的代码:\n{code}\n{prompt_user}'
		
		prompt_system = format_prompt(prompt_system, variables, code=code)
		prompt_user = format_prompt(prompt_user, variables, code=code)
		return prompt_system, prompt_user
	else:
		return None, None
	
def send_task_to_sqs(event, rules, request_id, commit_id, contents, variables=None):

	# 更新记录的任务总数
	count = len(contents)
	log.info('Final count: {}'.format(count))
	log.info('Commit Id, Request Id: {}, {}'.format(commit_id, request_id))
	try:
		table_name = os.getenv('REQUEST_TABLE')
		table = dynamodb.Table(table_name)
		table.update_item(
			Key = dict(commit_id=commit_id, request_id=request_id),
			UpdateExpression = "set #s = :s, update_time = :t, task_complete = :tc, task_failure = :tf, task_total = :tt, report_s3key = :rs, report_url = :ru",
			ExpressionAttributeNames = { '#s': 'task_status' },
			ExpressionAttributeValues = {
				':s': 'Initializing',
				':t': str(datetime.datetime.now()),
				':tc': 0,
				':tf': 0,
				':tt': count,
				':rs': '',
				':ru': '',
			},
			ReturnValues = "ALL_NEW",
		)
		item = dynamodb.Table(table_name).get_item(Key=dict(commit_id=commit_id, request_id=request_id), ConsistentRead=True).get('Item')
		log.info('Test Item.', extra=dict(item={ k: str(item[k]) for k in item }))
	except Exception as ex:
		log.error(f'Fail to update status for request record(commit_id={commit_id}), request_id={request_id}).', extra=dict(exception=str(ex)))
		return False
		
	# 每一个content与每一个rule组合成一个Bedrock Task
	# 刚写完，准备deploy一次，然后看看效果吧。应该每次request，只管branch，不管mode，所有mode都会执行一次。
	number = 0
	for content in contents:
		mode = content.get('mode')
		rule = content.get('rule')
		result = True
		try:
			model = rule.get('model')
			prompt_system, prompt_user = get_prompt_data(mode, rule, content.get('content'), variables)
			log.info(f'Make up new prompt.', extra=dict(prompt_system=prompt_system, prompt_user=prompt_user))
			if not prompt_user: continue
		
			number += 1
			rule_name = rule.get('name', 'none')
			identity = '{}-{}-{}-{}-{}'.format(mode, model, number, rule_name, content.get('filepath', 'none')).lower()
			item = dict(
				context = event, 
				commit_id = commit_id, 
				request_id = request_id,
				number = number,
				mode = mode, 
				model = model,
				identity = identity,
				filepath = content.get('filepath'),
				rule_name = rule_name,
				prompt_system = prompt_system,
				prompt_user = prompt_user,
			)
			if event.get('confirm', False) and event.get('confirm_prompt'):
				item['confirm_prompt'] = event.get('confirm_prompt')
			result = send_message(item)
			if not result:
				log.info('Fail to send bedrock task to SQS')
		except Exception as ex:
			log.error(f'Fail to create SQS task.', extra=dict(exception=str(ex)))
			result = False
		
		if not result:
			try:
				table.update_item(
					Key=dict(commit_id=commit_id, request_id=request_id),
					UpdateExpression="set task_failure = task_failure + :tf",
					ExpressionAttributeValues={ ':tf': 1 },
					ReturnValues="ALL_NEW",
				)
			except Exception as ex:
				log.error(f'Fail to update FAILURE COUNT for commit_id({commit_id}) and mode({mode}).', extra=dict(exception=str(ex)))

	return True

def update_dynamodb_status(commit_id, scan_scope, status, file_num):
	
	key = { 'commit_id': commit_id, 'scan_scope': scan_scope }
	
	# 检查数据存在性
	table_name = os.getenv('REQUEST_TABLE')
	table = dynamodb.Table(table_name)
	item = table.get_item(Key=key)
	if item.get('Item') is None:
		raise Exception(f'Cannot find record for COMMIT ID({commit_id}) and SCAN SCOPE({scan_scope}).')
	
	# 更新数据
	table.update_item(
		Key=key,
		UpdateExpression="set task_status = :s, update_at = :t, file_num = file_num + :m",
		ExpressionAttributeValues={
			":s": status,
			":t": str(datetime.datetime.now()),
			":m": file_num,
		},
		ReturnValues="ALL_NEW",
	)


def validate_sqs_event(event):
	"""
	mode = all
	mode = single，commit_id, previous_commit_id
	"""
	required = [ 'request_id' ]
		
	for field in required:
		if field not in event:
			raise Exception(f'SQS event does not have field {field} - {event}')
	return True

def update_project_name(commit_id, request_id, project_name):
	datetime_str = str(datetime.datetime.now())
	table_name = os.getenv('REQUEST_TABLE')
	dynamodb.Table(table_name).update_item(
		Key = { 'commit_id': commit_id, 'request_id': request_id },
		UpdateExpression = 'set project_name = :pn, update_time = :t',
		ExpressionAttributeValues = { ':pn': project_name, ':t': datetime_str },
		ReturnValues = 'ALL_NEW'
	)

def load_rules(event, repo_context, commit_id=None, branch=None):
	if event.get('invoker') == 'webtool':
		rules = [
			{
				"name": event.get("rule_name"),
				"mode": event.get('mode'),
				"number": 1,
				"model": event.get('model'),
				"event": event.get('event_type'),
				"branch": event.get('target_branch'),
				"target": event.get('target'),
				"confirm": event.get('confirm', False),
				"prompt_system": event.get('webtool_prompt_system'),
				"prompt_user": event.get('webtool_prompt_user')
			}
		]
		log.info(f'Make up rule for webtool.', extra=dict(rules=rules))
	else:
		rules = codelib.get_rules(repo_context, commit_id, branch)
	return rules

def get_targets(rule):
	targets = [t.strip() for t in rule.get('target', '').strip().rstrip('.').split(',')]
	return targets

def get_code_contents_for_all(repo_context, commit_id, rule):
	targets = get_targets(rule)
	text = codelib.get_project_code_text(repo_context, commit_id, targets)      # 计算完整的代码块
	contents = []
	if text:
		contents.append(dict(mode='all', filepath = '<The Whole Project>', content=text, rule=rule))
	return contents

def get_code_contents_for_single(repo_context, commit_id, previous_commit_id, rule):
	# 获取涉及的文件
	targets = get_targets(rule)
	file_diffs = codelib.get_involved_files(repo_context, commit_id, previous_commit_id)
	files = list(file_diffs.keys())
	log.info(f'Get {len(files)} involved files before filtering.', extra=dict(files=files))
	files = base.filter_targets(files, targets)
	log.info(f'Filter {len(files)} files.', extra=dict(files=files, targets=targets))

	# 逐个文件组装成提示词片段
	contents = []
	for filepath in files:
		code = codelib.get_repository_file(repo_context, filepath, commit_id)
		content = f'{filepath}\n```\n{code}\n```'
		contents.append(dict(mode='single', filepath = filepath, content = content, rule=rule))
	return contents

def get_code_contents_for_diff(repo_context, commit_id, previous_commit_id, rule):
	# 获取涉及的文件
	targets = get_targets(rule)
	file_diffs = codelib.get_involved_files(repo_context, commit_id, previous_commit_id)
	files = list(file_diffs.keys())
	log.info(f'Get {len(files)} involved files before filtering.', extra=dict(files=files))
	files = base.filter_targets(files, targets)
	log.info(f'Filter {len(files)} files.', extra=dict(files=files, targets=targets))

	# 逐个文件组装成提示词片段
	contents = []
	for filepath in files:
		diff = file_diffs.get(filepath)
		content = f'{filepath}\n```\n{diff}\n```'
		contents.append(dict(mode='diff', filepath = filepath, content = content, rule=rule))
	return contents

def lambda_handler(event, context):
	
	log.info(event, extra=dict(label='event'))
	
	# 校验SQS Event必要字段
	try:
		validate_sqs_event(event)
	except Exception as ex:
		log.error(f'Fail to validate SQS event.', extra=dict(exception=str(ex)))
		return {"statusCode": 500, "body": str(ex)}
	
	# 初始化变量
	# mode            = event['mode']
	commit_id       = event['commit_id']
	request_id 		= event['request_id']
	event_type		= event.get('event_type')
	invoker			= event.get('invoker')
	target_branch	= event.get('target_branch')
	target			= event.get('target')
	project_name	= event.get('project_name')
	previous_commit_id 	= event.get('previous_commit_id')
	
	# 获取Code Lib Context
	repo_context = codelib.init_repo_context(event)

	# 格式化commit id
	cid = codelib.format_commit_id(repo_context, target_branch, previous_commit_id)
	if previous_commit_id != cid:
		log.info(f'Set previous_commit_id from {previous_commit_id} to commit id({cid})')
		previous_commit_id = cid
	cid = codelib.format_commit_id(repo_context, target_branch, commit_id)
	if commit_id != cid:
		log.info(f'Set commit_id from {commit_id} to commit id({cid})')
		commit_id = cid
	
	try:
		name = repo_context.get('project').name
		if name != project_name:
			log.info(f'Project name({name}) does not equals provided({project_name}). Try to update project name to {name}.' )
			update_project_name(commit_id, request_id, name)
	except Exception as ex:
		log.error(f'Fail to update project name.', extra=dict(exception=str(ex)))

	# 解析.codereview规则
	all_rules = load_rules(event, repo_context, commit_id=commit_id, branch=target_branch)
	rules = []
	for rule in all_rules:
		if match_branch(rule.get('branch'), target_branch) and rule.get('event') == event_type:
			rules.append(rule)
	log.info(f'Found {len(rules)} rules for branch({target_branch})', extra=dict(rule_names=[rule.get('name') for rule in rules]))
	modes = list({rule.get('mode') for rule in rules})
	log.info('Found {} modes for branch({}): {}'.format(len(modes), target_branch, modes))
	
	# contents_with_mode = dict()
	contents = []
	for rule in rules:
		mode = rule.get('mode')
		
		rule_contents = []
		if mode == 'all':
			rule_contents = get_code_contents_for_all(repo_context, commit_id, rule)
		elif mode == 'single':
			rule_contents = get_code_contents_for_single(repo_context, commit_id, previous_commit_id, rule)
		elif mode == 'diff':
			rule_contents = get_code_contents_for_diff(repo_context, commit_id, previous_commit_id, rule)
		
		log.info(f'Get {len(rule_contents)} contents for rule({rule.get("name")}).', extra=dict(contents=rule_contents))
		contents = contents + rule_contents

	log.info(f'Get {len(contents)} prompt segments for involved files', extra=dict(contents=contents))
	# contents = None # to del
	if contents:
		result = send_task_to_sqs(event, rules, request_id, commit_id, contents)
	else:
		try:
			datetime_str = str(datetime.datetime.now())
			table_name = os.getenv('REQUEST_TABLE')
			dynamodb.Table(table_name).update_item(
				Key = { 'commit_id': commit_id, 'request_id': request_id },
				UpdateExpression = 'set task_status = :s, task_complete = :tc, task_failure = :tf, task_total = :tt, update_time = :t',
				ExpressionAttributeValues = { ':s': base.STATUS_COMPLETE, ':tf': 0, ':tc': 0, ':tt': 0, ':t': datetime_str },
				ReturnValues = 'ALL_NEW'
			)
			event = dict(commit_id = commit_id, request_id = request_id)
			context = dict(project_name=project_name)
			if invoker == 'webtool':
				report.generate_report_and_notify(None, event, context)
			result = True
		except Exception as ex:
			log.error(f'Fail to update REQUEST COMPLETE for commit_id({commit_id}) and request_id({request_id}).', extra=dict(exception=str(ex)))
			result = False

	log.info(f'Complete task dispatching for request({request_id}).')

	return base.response_success(None)
