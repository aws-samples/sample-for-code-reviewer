import gitlab.exceptions
import os, json, yaml, logging
import gitlab
import base
from gitlab.exceptions import GitlabHttpError
from logger import init_logger

DEFAULT_MODE 			= os.getenv('DEFAULT_MODE', 'all')
DEFAULT_MODEL 			= os.getenv('DEFAULT_MODEL', 'claude3')

init_logger()
log = logging.getLogger('crlog_{}'.format(__name__))

def parse_gitlab_errcode(ex):
	if isinstance(ex, gitlab.exceptions.GitlabAuthenticationError):
		return 'AuthenticationError'
	elif isinstance(ex, gitlab.exceptions.GitlabGetError) or \
		isinstance(ex, gitlab.exceptions.GitlabCreateError) or \
		isinstance(ex, gitlab.exceptions.GitlabUpdateError):
		if ex.response_code == 401: 
			return 'Unauthorized'
		elif ex.response_code == 403: 
			return 'Forbidden'
		elif ex.response_code == 404: 
			return 'NotFound'
	return 'Unknow'

def get_diff_files(project, from_commit_id, to_commit_id):
	comparison = project.repository_compare(from_commit_id, to_commit_id)
	commits = comparison['diffs']
	files = {}
	for item in commits:
		if item['new_file']:
			files[item['new_path']] = item['diff']
		elif item['renamed_file']:
			if item['old_path'] in files: 
				del files[item['old_path']]
			files[item['new_path']] = item['diff']
		elif item['deleted_file']:
			if item['new_path'] in files:
				del files[item['new_path']]
		else:
			files[item['new_path']] = item['diff']
	return files


def format_web_url(web_url):
	return web_url[:-4] if web_url and web_url.endswith('.git') else web_url
	
def calculate_repo_url(web_url, path_with_namespace):
	if web_url and path_with_namespace:
		if len(web_url) > len(path_with_namespace):
			return web_url[:-len(path_with_namespace)]
		else:
			log.info(f'Fail to calculate repo_url, the length of web_url({web_url}) is not greater than path_with_namespace({path_with_namespace}).')
	else:
		log.info(f'Fail to calculate repo_url, web_url({web_url}) or path_with_namespace({path_with_namespace}) is not provided.')
	return None

def parse_gitlab_webtool_parameters(event):
	body = json.loads(event.get('body', '{}'))
	keys = [ 'mode', 'model', 'event_type', 'web_url', 'path_with_namespace', 'target_branch', 'ref', 'commit_id', 'previous_commit_id', 'private_token', 'target', 'rule_name', 'confirm', 'confirm_prompt' ]
	params = { key: body.get(key) for key in keys }
	params['source'] = 'gitlab'
	params['project_name'] = 'Test Project'
	params['project_id'] = params.get('path_with_namespace')
	params['web_url'] = format_web_url(params['web_url'])
	params['repo_url'] = calculate_repo_url(params.get('web_url'), params.get('path_with_namespace'))
	params['username'] = 'mock'
	params['webtool_prompt_system'] = body.get('prompt_system')
	params['webtool_prompt_user'] = body.get('prompt_user')
	if not params.get('target'):
		params['target'] = '**'
	return params

def parse_gitlab_parameters(event):
	
	body = json.loads(event.get('body', '{}'))
	event_type = body.get('object_kind', '').lower()
	log.info(f'Received Gitlab event[{event_type}].', extra=dict(body=body))

	headers = event.get('headers', {})
	
	body_project = body.get('project', {})
	web_url = body_project.get('web_url')
	path_with_namespace = body_project.get('path_with_namespace')
	repo_url = web_url[:-len(path_with_namespace)]

	# 计算Target branch
	target_branch = None
	if event_type == 'push':
		target_branch = body.get('ref')
		if target_branch.startswith('refs/heads/'):
			target_branch = target_branch[11:]
		else:
			log.info(f'Can\'t determine target branch for the field "ref" does not meet the expected format: {body}')
	elif event_type == 'merge_request':
		target_branch = body.get('object_attributes', {}).get('target_branch')
	
	params=dict(
		source = 'gitlab',
		web_url = web_url,
		project_id = body_project.get('id'),
		project_name = body_project.get('name'),
		repo_url = repo_url,
		private_token = headers.get('X-Gitlab-Token'),
		target_branch = target_branch,
		event_type = event_type
	)
	if not params.get('project_id'):
		params['project_id'] = body_project.get('path_with_namespace')

	if event_type == 'push':
		params['commit_id'] = body.get('after')
		params['previous_commit_id'] = body.get('before')
		params['ref'] = body.get('ref')
		params['username'] = body.get('user_username')
	elif event_type == 'merge_request':
		params['event_type'] = 'merge'
		merge_status = body.get('object_attributes', {}).get('merge_status')
		if merge_status in  ['checking']:
			params['commit_id'] = body.get('object_attributes', {}).get('last_commit', {}).get('id')
			params['ref'] = body.get('object_attributes', {}).get('source_branch')
			params['username'] = body.get('user', {}).get('username')
			log.info(f'The merge status is {merge_status}, it is going to invoke code review.')	
		else:
			params['commit_id'] = None
			params['ref'] = None
			params['username'] = None
			log.info(f'The merge status is {merge_status}, it will skip code review.')	

	if params.get('commit_id') is None: 
		params['commit_id'] = ''

	return params
	
def get_gitlab_file(project, path, ref):
	try:
		log.info(f'Try to get gitlab file in ref({ref}): {path}')
		content = project.files.raw(file_path=path, ref=ref)
		log.info(f'Got gitlab file {path} @ {ref}: {content}')
		return content.decode()
	except Exception as ex:
		log.error(f'Fail to get git file {path} @ {ref}.', extra=dict(exception=str(ex)))
		return None

def get_gitlab_file_content(project, file_path, ref_name):
	file_content = project.files.raw(file_path=file_path, ref=ref_name).decode()
	log.info(f'Getting file content({file_path}).', extra=dict(content=file_content))
	return file_content

def get_rules(project, commit_id, branch):
	folder = '.codereview'
	ref = commit_id if commit_id else branch
	try:
		items = project.repository_tree(path=folder, ref=ref, recursive=True)
		filenames = [ item.get('name') for item in items if item['name'].lower().endswith('.yaml') ]
	except Exception as ex:
		if isinstance(ex, gitlab.exceptions.GitlabGetError) and ex.response_code == 404: 
			log.info(f'Directory .codereview is not in repository for commit id {commit_id}')
			filenames = []
		else:
			raise base.CodelibException(f'Fail to get rules: {ex}', code=parse_gitlab_errcode(ex)) from ex
	
	rules = []
	for filename in filenames:
		path = f'.codereview/{filename}'
		file_content = get_gitlab_file_content(project, path, ref)
		content = yaml.safe_load(file_content) if file_content else dict()
		content['filename'] = filename
		rules.append(content)

	return rules

def put_rule(project, branch, filepath, content):
	
	# 先尝试获取文件
	file = None
	try:
		log.info(f'Try to get file {filepath} in ref({branch}).')
		file = project.files.get(file_path=filepath, ref=branch)
		log.info(f'File {filepath} exists in ref({branch}).')
	except Exception as ex:
		if isinstance(ex, gitlab.exceptions.GitlabGetError) and ex.response_code == 404: 
			file = None
		else:
			raise base.CodelibException(f'Fail to get rules: {ex}', code=parse_gitlab_errcode(ex)) from ex
	
	# 然后更新文件
	try:
		if file:
			file.content = base.encode_base64(content)
			log.info(f'Try to update file {filepath} in ref({branch}).', extra=dict(content=content))
			file.save(branch=branch, commit_message="Update codereview yaml", encoding='base64')
			log.info(f"File {filepath} updated successfully.")
		else:
			log.info(f'Try to create file {filepath} in ref({branch}).', extra=dict(content=content))
			project.files.create({ 'file_path': filepath, 'branch': branch, 'content': content, 'commit_message': "Create codereview yaml" })
			log.info(f"File {filepath} created successfully.")
	except Exception as ex:
		raise base.CodelibException(f'Fail to save rule: {ex}', code=parse_gitlab_errcode(ex)) from ex

def get_last_commit_id(project, branch):
	branch = project.branches.get(branch)
	latest_commit_id = branch.commit['id']
	return latest_commit_id

def get_first_commit_id(project, branch):
	commits = project.commits.list(ref_name=branch, all=True, order_by='created_date', sort='desc')
	first_commit_id = next((commit.id for commit in commits if not commit.parent_ids), None)
	return first_commit_id

def init_gitlab_context(repo_url, project_id, private_token):
	try:
		log.info(f'Try to init gitlab connection for repo({repo_url}).')
		gl = gitlab.Gitlab(repo_url if repo_url else None, private_token=private_token)
		log.info(f'Try to get project({project_id})')
		project = gl.projects.get(project_id)
		return project
	except Exception as ex:
		raise base.CodelibException(f'Fail to init Gitlab context: {ex}', code=parse_gitlab_errcode(ex)) from ex
	
def get_project_code_text(repo_context, commit_id, targets):
	
	project = repo_context
	
	# 用于存储文件路径的数组
	items = project.repository_tree(ref=commit_id, all=True, recursive=True)
	file_paths = base.filter_targets([ item['path'] for item in items if item['type'] == 'blob'], targets)
	log.info('Scaned {} files after ext filtering in repository for commit_id({}), filters({}).'.format(len(file_paths), commit_id, targets))

	text = ''
	for file_path in file_paths:
		try:
			file_content = get_gitlab_file_content(project, file_path, commit_id)
			section = f'{file_path}\n```\n{file_content}\n```'
			text = '{}\n\n{}'.format(text, section) if text else section			
		except Exception as ex:
			log.info(f'Fail to get file({file_path}) content.', extra=dict(exception=str(ex)))
  
	return text
