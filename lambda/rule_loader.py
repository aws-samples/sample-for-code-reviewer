import logging
import base, codelib
from logger import init_logger

init_logger()
log = logging.getLogger('crlog_{}'.format(__name__))

def lambda_handler(event, context):
	
	log.info(event, extra=dict(label='event'))
	response_headers = {
		"Access-Control-Allow-Headers" : "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,x-gitlab-token",
		"Access-Control-Allow-Origin": "*",
		"Access-Control-Allow-Methods": "OPTIONS,GET"
	}

	parameters = event.get('queryStringParameters', {})
	
	branch 	= parameters.get('target_branch')
	repo_url = parameters.get('repo_url')
	
	# 优先使用前端传递的source参数，否则根据repo_url检测仓库类型
	source = parameters.get('source')
	if not source:
		source = 'github' if repo_url and 'github.com' in repo_url else 'gitlab'

	event_object = dict(
		source = source,
		repo_url = repo_url,
		project_id = parameters.get('project_id'),
		private_token = parameters.get('private_token'),
		target_branch = branch
	)

	headers = event.get('headers', {})
	# 根据仓库类型获取对应的token
	if source == 'github':
		header_private_token = headers.get('X-GitHub-Token') or headers.get('x-github-token')
	else:
		header_private_token = headers.get('X-Gitlab-Token') or headers.get('x-gitlab-token')
	if header_private_token:
		event_object['private_token'] = header_private_token

	try:
		repo_context = codelib.init_repo_context(event_object)
		rules = codelib.get_rules(repo_context, None, branch)
	except base.CodelibException as ex:
		log.info('Occur codelib exception.', extra=dict(exception=str(ex)))
		return { 'statusCode': 200, 'headers': response_headers, 'body': base.dump_json(dict(succ=False, message=ex.code)) }
	
	return { 'statusCode': 200, 'body': base.dump_json(dict(succ=True, data=rules)), "headers": response_headers }
