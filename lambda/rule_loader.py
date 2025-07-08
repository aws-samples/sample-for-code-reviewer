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

	event_object = dict(
		repo_url = parameters.get('repo_url'),
		project_id = parameters.get('project_id'),
		private_token = parameters.get('private_token'),
		target_branch = branch
	)

	headers = event.get('headers', {})
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
