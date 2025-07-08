import base, codelib, json, logging
from logger import init_logger

init_logger()
log = logging.getLogger('crlog_{}'.format(__name__))

def lambda_handler(event, context):
	
	log.info(event, extra=dict(label='event'))

	filename = event.get('pathParameters', {}).get('filename')
	body = json.loads(event.get('body', '{}'))
	branch = body.get('target_branch')
	content = body.get('content')

	event_object = dict(
		repo_url = body.get('repo_url'),
		project_id = body.get('project_id'),
		private_token = body.get('private_token'),
		target_branch = branch,
	)

	headers = event.get('headers', {})
	header_private_token = base.get_access_token(headers)
	if header_private_token:
		event_object['private_token'] = header_private_token

	try:
		repo_context = codelib.init_repo_context(event_object)
		filepath = f'.codereview/{filename}'
		codelib.put_rule(repo_context, branch, filepath, content)
	except base.CodelibException as ex:
		log.info('Occur codelib exception.', extra=dict(exception=str(ex)))
		return base.response_failure(ex.code, cors_method='PUT')
	
	return base.response_success(None, cors_method='PUT')

