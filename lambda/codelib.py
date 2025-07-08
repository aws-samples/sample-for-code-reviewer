import datetime
import gitlab_code

def init_repo_context(params):
	"""
	{ repo_url, project_id, private_token }
	"""
	source = 'gitlab' # Change to parse from params.
	if source == 'gitlab':
		project = gitlab_code.init_gitlab_context(params.get('repo_url'), params.get('project_id'), params.get('private_token'))
		return dict(source='gitlab', project=project)
	else:
		raise Exception(f'Code lib source({source}) is not support yet.')

def parse_webtool_parameters(event):
	source = 'gitlab'
	if source == 'gitlab':
		params = gitlab_code.parse_gitlab_webtool_parameters(event)
		date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
		params['request_id'] = '{}_{}_{}'.format(date_str, params['source'], params['username'])
		params['invoker'] = 'webtool'
		return params
	else:
		raise Exception(f'Code lib source({source}) is not support yet.')

def parse_parameters(event):
	source = 'gitlab'
	if source == 'gitlab':
		params = gitlab_code.parse_gitlab_parameters(event)
		date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
		params['request_id'] = '{}_{}_{}'.format(date_str, params['source'], params['username'])
		return params
	else:
		raise Exception(f'Code lib source({source}) is not support yet.')

def get_project_code_text(repo_context, commit_id, targets):
	source = repo_context.get('source')
	if source == 'gitlab':
		return gitlab_code.get_project_code_text(repo_context.get('project'), commit_id, targets)
	else:
		raise Exception(f'Code lib source({source}) is not support yet.')

def get_involved_files(repo_context, commit_id, previous_commit_id):
	source = repo_context.get('source')
	if source == 'gitlab':
		files = gitlab_code.get_diff_files(repo_context.get('project'), previous_commit_id, commit_id)
		return files
	else:
		raise Exception(f'Code lib source({source}) is not support yet.')

def get_involved_diffs(repo_context, commit_id, previous_commit_id):
	source = repo_context.get('source')
	if source == 'gitlab':
		files = gitlab_code.get_diff_files(repo_context.get('project'), previous_commit_id, commit_id)
		return files
	else:
		raise Exception(f'Code lib source({source}) is not support yet.')

def get_repository_file(repo_context, filepath, commit_id):
	source = repo_context.get('source')
	if source == 'gitlab':
		return gitlab_code.get_gitlab_file(repo_context.get('project'), filepath, commit_id)
	else:
		raise Exception(f'Code lib source({source}) is not support yet.')

def get_rules(repo_context, commit_id, branch):
	source = repo_context.get('source')
	if source == 'gitlab':
		files = gitlab_code.get_rules(repo_context.get('project'), commit_id, branch)
		return files
	else:
		raise Exception(f'Code lib source({source}) is not support yet.')

def put_rule(repo_context, branch, filepath, content):
	source = repo_context.get('source')
	if source == 'gitlab':
		gitlab_code.put_rule(repo_context.get('project'), branch, filepath, content)
	else:
		raise Exception(f'Code lib source({source}) is not support yet.')

def get_last_commit_id(repo_context, branch):
	source = repo_context.get('source')
	if source == 'gitlab':
		return gitlab_code.get_last_commit_id(repo_context.get('project'), branch)
	else:
		raise Exception(f'Code lib source({source}) is not support yet.')

def get_first_commit_id(repo_context, branch):
	source = repo_context.get('source')
	if source == 'gitlab':
		return gitlab_code.get_first_commit_id(repo_context.get('project'), branch)
	else:
		raise Exception(f'Code lib source({source}) is not support yet.')

def is_first_commit_id_alias(commit_id):
	return commit_id == '1' or commit_id == 'first'

def format_commit_id(repo_context, branch, commit_id):
	if not commit_id:
		return get_last_commit_id(repo_context, branch)
	elif is_first_commit_id_alias(commit_id):
		return get_first_commit_id(repo_context, branch)
	else:
		return commit_id
