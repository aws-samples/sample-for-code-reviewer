import datetime
import json
import os
import gitlab_code
import github_code

def detect_source_from_event(event):
	"""
	从webhook事件中自动检测仓库源
	
	参数:
		event: webhook事件对象，包含headers和body
		
	返回:
		str: 仓库源类型 ('github' 或 'gitlab')
		
	检测逻辑:
		1. 对于Web工具请求，检查body中的source参数
		2. 检查headers中的X-GitHub-Event标识GitHub webhook
		3. 检查headers中的X-Gitlab-Event标识GitLab webhook  
		4. 如果都没有，使用环境变量DEFAULT_REPO_SOURCE的配置
		5. 如果环境变量也没有配置，默认使用'gitlab'
	"""
	headers = event.get('headers', {})
	
	# 对于Web工具请求，检查body中的source参数
	body = event.get('body')
	if body:
		try:
			body_data = json.loads(body)
			if 'source' in body_data:
				return body_data['source']
		except:
			pass
	
	# GitHub webhook特征检测
	if 'X-GitHub-Event' in headers:
		return 'github'
	# GitLab webhook特征检测  
	elif 'X-Gitlab-Event' in headers:
		return 'gitlab'
	# 默认回退到配置的默认源
	else:
		default_source = os.getenv('DEFAULT_REPO_SOURCE', 'gitlab')
		return default_source

def init_repo_context(params):
	"""
	初始化仓库上下文
	
	参数:
		params: 包含仓库信息的参数字典
			- source: 仓库源类型 ('gitlab' 或 'github')
			- repo_url: 仓库URL
			- project_id: 项目ID
			- private_token: 访问令牌
			
	返回:
		dict: 仓库上下文字典
			- source: 仓库源类型
			- project: 仓库对象 (GitLab Project 或 GitHub Repository)
	"""
	source = params.get('source') or detect_source_from_event(params)
	
	if source == 'gitlab':
		project = gitlab_code.init_gitlab_context(params.get('repo_url'), params.get('project_id'), params.get('private_token'))
		return dict(source='gitlab', project=project)
	elif source == 'github':
		repository = github_code.init_github_context(params.get('repo_url'), params.get('project_id'), params.get('private_token'))
		return dict(source='github', project=repository)
	else:
		raise Exception(f'Code lib source({source}) is not supported yet.')

def parse_webtool_parameters(event):
	"""
	解析Web工具请求参数
	
	参数:
		event: Web工具请求事件对象
		
	返回:
		dict: 标准化的参数字典
	"""
	source = detect_source_from_event(event)
	
	if source == 'gitlab':
		params = gitlab_code.parse_gitlab_webtool_parameters(event)
	elif source == 'github':
		params = github_code.parse_github_webtool_parameters(event)
	else:
		raise Exception(f'Code lib source({source}) is not supported yet.')
	
	# 生成请求ID和设置调用者
	date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
	params['request_id'] = '{}_{}_{}'.format(date_str, params['source'], params['username'])
	params['invoker'] = 'webtool'
	return params

def parse_parameters(event):
	"""
	解析webhook事件参数
	
	参数:
		event: webhook事件对象
		
	返回:
		dict: 标准化的参数字典
	"""
	source = detect_source_from_event(event)
	
	if source == 'gitlab':
		params = gitlab_code.parse_gitlab_parameters(event)
	elif source == 'github':
		params = github_code.parse_github_parameters(event)
	else:
		raise Exception(f'Code lib source({source}) is not supported yet.')
	
	# 生成请求ID
	date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
	params['request_id'] = '{}_{}_{}'.format(date_str, params['source'], params['username'])
	return params

def get_project_code_text(repo_context, commit_id, targets):
	"""
	获取项目代码文本
	
	参数:
		repo_context: 仓库上下文字典
		commit_id: 提交ID
		targets: 目标文件模式列表
		
	返回:
		str: 格式化的代码文本
	"""
	source = repo_context.get('source')
	if source == 'gitlab':
		return gitlab_code.get_project_code_text(repo_context.get('project'), commit_id, targets)
	elif source == 'github':
		return github_code.get_project_code_text(repo_context.get('project'), commit_id, targets)
	else:
		raise Exception(f'Code lib source({source}) is not supported yet.')

def get_involved_files(repo_context, commit_id, previous_commit_id):
	"""
	获取涉及的文件列表
	
	参数:
		repo_context: 仓库上下文字典
		commit_id: 当前提交ID
		previous_commit_id: 前一个提交ID
		
	返回:
		dict: 文件路径到差异内容的映射
	"""
	source = repo_context.get('source')
	if source == 'gitlab':
		files = gitlab_code.get_diff_files(repo_context.get('project'), previous_commit_id, commit_id)
		return files
	elif source == 'github':
		files = github_code.get_diff_files(repo_context.get('project'), previous_commit_id, commit_id)
		return files
	else:
		raise Exception(f'Code lib source({source}) is not supported yet.')

def get_involved_diffs(repo_context, commit_id, previous_commit_id):
	"""
	获取涉及的文件差异
	
	参数:
		repo_context: 仓库上下文字典
		commit_id: 当前提交ID
		previous_commit_id: 前一个提交ID
		
	返回:
		dict: 文件路径到差异内容的映射
	"""
	source = repo_context.get('source')
	if source == 'gitlab':
		files = gitlab_code.get_diff_files(repo_context.get('project'), previous_commit_id, commit_id)
		return files
	elif source == 'github':
		files = github_code.get_diff_files(repo_context.get('project'), previous_commit_id, commit_id)
		return files
	else:
		raise Exception(f'Code lib source({source}) is not supported yet.')

def get_repository_file(repo_context, filepath, commit_id):
	"""
	获取仓库文件内容
	
	参数:
		repo_context: 仓库上下文字典
		filepath: 文件路径
		commit_id: 提交ID
		
	返回:
		str: 文件内容，失败时返回None
	"""
	source = repo_context.get('source')
	if source == 'gitlab':
		return gitlab_code.get_gitlab_file(repo_context.get('project'), filepath, commit_id)
	elif source == 'github':
		return github_code.get_github_file(repo_context.get('project'), filepath, commit_id)
	else:
		raise Exception(f'Code lib source({source}) is not supported yet.')

def get_rules(repo_context, commit_id, branch):
	"""
	获取评审规则
	
	参数:
		repo_context: 仓库上下文字典
		commit_id: 提交ID
		branch: 分支名
		
	返回:
		list: 规则列表
	"""
	source = repo_context.get('source')
	if source == 'gitlab':
		files = gitlab_code.get_rules(repo_context.get('project'), commit_id, branch)
		return files
	elif source == 'github':
		files = github_code.get_rules(repo_context.get('project'), commit_id, branch)
		return files
	else:
		raise Exception(f'Code lib source({source}) is not supported yet.')

def put_rule(repo_context, branch, filepath, content):
	"""
	创建或更新规则文件
	
	参数:
		repo_context: 仓库上下文字典
		branch: 分支名
		filepath: 文件路径
		content: 文件内容
	"""
	source = repo_context.get('source')
	if source == 'gitlab':
		gitlab_code.put_rule(repo_context.get('project'), branch, filepath, content)
	elif source == 'github':
		github_code.put_rule(repo_context.get('project'), branch, filepath, content)
	else:
		raise Exception(f'Code lib source({source}) is not supported yet.')

def get_last_commit_id(repo_context, branch):
	"""
	获取分支的最新提交ID
	
	参数:
		repo_context: 仓库上下文字典
		branch: 分支名
		
	返回:
		str: 最新提交ID
	"""
	source = repo_context.get('source')
	if source == 'gitlab':
		return gitlab_code.get_last_commit_id(repo_context.get('project'), branch)
	elif source == 'github':
		return github_code.get_last_commit_id(repo_context.get('project'), branch)
	else:
		raise Exception(f'Code lib source({source}) is not supported yet.')

def get_first_commit_id(repo_context, branch):
	"""
	获取分支的首次提交ID
	
	参数:
		repo_context: 仓库上下文字典
		branch: 分支名
		
	返回:
		str: 首次提交ID
	"""
	source = repo_context.get('source')
	if source == 'gitlab':
		return gitlab_code.get_first_commit_id(repo_context.get('project'), branch)
	elif source == 'github':
		return github_code.get_first_commit_id(repo_context.get('project'), branch)
	else:
		raise Exception(f'Code lib source({source}) is not supported yet.')

def is_first_commit_id_alias(commit_id):
	return commit_id == '1' or commit_id == 'first'

def format_commit_id(repo_context, branch, commit_id):
	if not commit_id:
		return get_last_commit_id(repo_context, branch)
	elif is_first_commit_id_alias(commit_id):
		return get_first_commit_id(repo_context, branch)
	else:
		return commit_id
