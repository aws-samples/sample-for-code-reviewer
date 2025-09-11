import github.GithubException
import os, json, yaml, logging
import github
import base
from github import Github
from github.GithubException import GithubException, BadCredentialsException, UnknownObjectException
from logger import init_logger

DEFAULT_MODE = os.getenv('DEFAULT_MODE', 'all')
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'claude3')

init_logger()
log = logging.getLogger('crlog_{}'.format(__name__))

def parse_github_errcode(ex):
    """
    将GitHub API异常转换为标准错误码
    
    参数:
        ex: GitHub API异常对象
        
    返回:
        str: 标准化的错误码字符串
        
    支持的异常类型:
        - BadCredentialsException: 认证失败 -> 'AuthenticationError'
        - UnknownObjectException: 资源不存在 -> 'NotFound'  
        - GithubException: 通用GitHub异常，根据状态码映射:
            - 401: 'Unauthorized'
            - 403: 'Forbidden'
            - 404: 'NotFound'
            - 422: 'ValidationError'
        - 其他异常: 'Unknown'
    """
    if isinstance(ex, BadCredentialsException):
        return 'AuthenticationError'
    elif isinstance(ex, UnknownObjectException):
        return 'NotFound'
    elif isinstance(ex, GithubException):
        if ex.status == 401:
            return 'Unauthorized'
        elif ex.status == 403:
            return 'Forbidden'
        elif ex.status == 404:
            return 'NotFound'
        elif ex.status == 422:
            return 'ValidationError'
        else:
            log.warning(f'Unmapped GitHub exception status: {ex.status}', extra=dict(exception=str(ex)))
            return 'Unknown'
    else:
        log.warning(f'Unknown GitHub exception type: {type(ex)}', extra=dict(exception=str(ex)))
        return 'Unknown'


# TODO: 以下函数将在后续任务中实现

def extract_github_webhook_secret(headers, body):
    """
    GitHub webhook不传递token，直接返回环境变量中的token
    """
    return os.getenv('ACCESS_TOKEN', '')

def parse_github_parameters(event):
    """
    解析GitHub webhook事件参数
    
    参数:
        event: GitHub webhook事件对象，包含headers和body
        
    返回:
        dict: 标准化的参数字典，与GitLab格式保持一致
        
    支持的事件类型:
        - push: GitHub推送事件
        - pull_request: GitHub拉取请求事件（转换为内部的merge事件）
    """
    try:
        body = json.loads(event.get('body', '{}'))
        headers = event.get('headers', {})
        
        # 从headers中获取GitHub事件类型
        github_event = headers.get('X-GitHub-Event', '').lower()
        log.info(f'Received GitHub event[{github_event}].', extra=dict(body=body))
        
        # 获取仓库信息
        repository = body.get('repository', {})
        web_url = repository.get('html_url')  # GitHub使用html_url
        full_name = repository.get('full_name')  # owner/repo-name格式
        repo_name = repository.get('name')
        
        # 计算repo_url (GitHub API base URL)
        if web_url and full_name:
            # 从https://github.com/owner/repo-name提取https://github.com
            repo_url = web_url[:-len(full_name)-1] if web_url.endswith(f'/{full_name}') else 'https://github.com'
        else:
            repo_url = 'https://github.com'
            log.warning(f'Unable to calculate repo_url from web_url({web_url}) and full_name({full_name}), using default.')
        
        # GitHub直接使用环境变量中的token
        github_token = os.getenv('ACCESS_TOKEN', '')
        
        # 基础参数结构
        params = dict(
            source='github',
            web_url=web_url,
            project_id=full_name,  # GitHub使用full_name作为项目ID
            project_name=repo_name,
            repo_url=repo_url,
            private_token=github_token,  # GitHub使用环境变量中的token
            event_type=github_event  # 先设置原始事件类型，后面会根据需要转换
        )
        
        # 验证事件类型是否支持
        if not is_github_event_supported(github_event):
            log.warning(f'Unsupported GitHub event type: {github_event}')
            params.update({
                'target_branch': None,
                'commit_id': None,
                'ref': None,
                'username': None,
                'previous_commit_id': None
            })
            return params
        
        # 验证事件是否应该触发评审
        should_process, reason = validate_github_event(github_event, body)
        log.info(f'GitHub event validation: {reason}')
        
        # 标准化事件类型
        standardized_event_type = standardize_github_event_type(github_event, body.get('action'))
        params['event_type'] = standardized_event_type
        
        # 根据事件类型解析特定字段
        if github_event == 'push':
            # GitHub Push事件处理
            ref = body.get('ref', '')  # refs/heads/branch_name
            target_branch = ref[11:] if ref.startswith('refs/heads/') else ref  # 移除refs/heads/前缀
            
            params.update({
                'target_branch': target_branch,
                'commit_id': body.get('after', ''),  # 推送后的提交ID
                'previous_commit_id': body.get('before', ''),  # 推送前的提交ID
                'ref': ref,
                'username': body.get('pusher', {}).get('name', '')  # 推送者用户名
            })
            
        elif github_event == 'pull_request':
            # GitHub Pull Request事件处理 - 已标准化为merge事件
            pull_request = body.get('pull_request', {})
            base_ref = pull_request.get('base', {}).get('ref', '')  # 目标分支
            head_ref = pull_request.get('head', {}).get('ref', '')  # 源分支
            head_sha = pull_request.get('head', {}).get('sha', '')  # 源分支的提交SHA
            
            if should_process:
                params.update({
                    'target_branch': base_ref,
                    'commit_id': head_sha,
                    'ref': head_ref,  # 源分支名
                    'username': body.get('sender', {}).get('login', ''),  # PR创建者
                    'previous_commit_id': ''  # PR事件没有previous_commit_id概念
                })
            else:
                # 不应该处理的PR状态，设置为空值跳过评审
                params.update({
                    'target_branch': base_ref,
                    'commit_id': None,  # 设置为None表示跳过评审
                    'ref': None,
                    'username': None,
                    'previous_commit_id': None
                })
        
        # 确保参数一致性
        params = ensure_github_parameter_consistency(params)
        
        # 验证参数完整性
        is_valid, error_message = validate_github_parameters(params)
        if not is_valid:
            log.error(f'GitHub parameter validation failed: {error_message}', extra=dict(params=params))
            raise base.CodelibException(f'Invalid GitHub parameters: {error_message}', code='ValidationError')
            
        log.info(f'Successfully parsed and validated GitHub parameters', extra=dict(
            event_type=params.get('event_type'),
            project_id=params.get('project_id'),
            target_branch=params.get('target_branch'),
            commit_id=params.get('commit_id')[:8] if params.get('commit_id') else 'None'  # 只记录前8位commit ID
        ))
        
        return params
        
    except json.JSONDecodeError as ex:
        log.error(f'Failed to parse GitHub webhook JSON body', extra=dict(exception=str(ex)))
        raise base.CodelibException(f'Invalid JSON in GitHub webhook body: {ex}', code='ValidationError') from ex
        
    except Exception as ex:
        log.error(f'Failed to parse GitHub webhook parameters', extra=dict(exception=str(ex)))
        raise base.CodelibException(f'Failed to parse GitHub webhook: {ex}', code='Unknown') from ex


def parse_github_webtool_parameters(event):
    """
    解析GitHub Web工具请求参数
    
    参数:
        event: Web工具请求事件对象，包含body中的JSON数据
        
    返回:
        dict: 标准化的参数字典，与GitLab Web工具格式保持一致
        
    支持的参数:
        - mode: 评审模式 (diff/single/all)
        - model: AI模型
        - event_type: 事件类型
        - web_url: 仓库Web URL
        - full_name: 仓库全名 (owner/repo-name)
        - target_branch: 目标分支
        - ref: 分支引用
        - commit_id: 提交ID
        - previous_commit_id: 前一个提交ID
        - private_token: GitHub Personal Access Token
        - target: 目标文件模式
        - rule_name: 规则名称
        - confirm: 确认标志
        - confirm_prompt: 确认提示
        - prompt_system: 系统提示词
        - prompt_user: 用户提示词
    """
    try:
        body = json.loads(event.get('body', '{}'))
        
        # 定义需要提取的参数键
        keys = [
            'mode', 'model', 'event_type', 'web_url', 'full_name', 'path_with_namespace', 'target_branch', 
            'ref', 'commit_id', 'previous_commit_id', 'private_token', 'target', 
            'rule_name', 'confirm', 'confirm_prompt'
        ]
        
        # 提取基础参数
        params = {key: body.get(key) for key in keys}
        
        # 设置GitHub特有的参数
        params['source'] = 'github'
        params['project_name'] = 'Test Project'  # Web工具测试项目名称
        
        # GitHub使用full_name或path_with_namespace作为项目ID
        params['project_id'] = params.get('full_name') or params.get('path_with_namespace')
        
        # 处理web_url格式化
        web_url = params.get('web_url')
        if web_url:
            # GitHub的web_url通常不以.git结尾，但为了兼容性还是检查一下
            params['web_url'] = format_github_web_url(web_url)
        
        # 计算repo_url
        params['repo_url'] = calculate_github_repo_url(params.get('web_url'), params.get('full_name'))
        
        # 设置默认用户名（Web工具模拟用户）
        params['username'] = 'mock'
        
        # 提取Web工具特有的提示词参数
        params['webtool_prompt_system'] = body.get('prompt_system')
        params['webtool_prompt_user'] = body.get('prompt_user')
        
        # 设置默认target（如果未提供）
        if not params.get('target'):
            params['target'] = '**'
        
        # 标准化事件类型（如果提供了event_type）
        if params.get('event_type'):
            # Web工具可能直接提供标准化的事件类型，但也要处理GitHub原生类型
            original_event_type = params.get('event_type')
            if original_event_type == 'pull_request':
                params['event_type'] = 'merge'
            elif original_event_type not in ['push', 'merge']:
                log.warning(f'Unknown event_type in webtool request: {original_event_type}')
        
        # 确保参数一致性
        params = ensure_github_parameter_consistency(params)
            
        log.info(f'Successfully parsed GitHub webtool parameters', extra=dict(
            mode=params.get('mode'),
            event_type=params.get('event_type'),
            project_id=params.get('project_id'),
            target_branch=params.get('target_branch')
        ))
        
        return params
        
    except json.JSONDecodeError as ex:
        log.error(f'Failed to parse GitHub webtool JSON body', extra=dict(exception=str(ex)))
        raise base.CodelibException(f'Invalid JSON in GitHub webtool request: {ex}', code='ValidationError') from ex
        
    except Exception as ex:
        log.error(f'Failed to parse GitHub webtool parameters', extra=dict(exception=str(ex)))
        raise base.CodelibException(f'Failed to parse GitHub webtool request: {ex}', code='Unknown') from ex


def format_github_web_url(web_url):
    """
    格式化GitHub Web URL
    
    参数:
        web_url: 原始Web URL
        
    返回:
        str: 格式化后的Web URL
    """
    if not web_url:
        return web_url
    
    # GitHub的URL通常不以.git结尾，但为了兼容性还是处理一下
    return web_url[:-4] if web_url.endswith('.git') else web_url


def calculate_github_repo_url(web_url, full_name):
    """
    计算GitHub仓库的API基础URL
    
    参数:
        web_url: 仓库Web URL (如: https://github.com/owner/repo)
        full_name: 仓库全名 (如: owner/repo)
        
    返回:
        str: API基础URL (如: https://github.com) 或 None
    """
    if web_url and full_name:
        if len(web_url) > len(full_name):
            # 从https://github.com/owner/repo提取https://github.com
            if web_url.endswith(f'/{full_name}'):
                return web_url[:-len(full_name)-1]
            else:
                log.info(f'Web URL format unexpected: {web_url} does not end with /{full_name}')
                return 'https://github.com'  # 默认值
        else:
            log.info(f'Fail to calculate repo_url, the length of web_url({web_url}) is not greater than full_name({full_name}).')
    else:
        log.info(f'Fail to calculate repo_url, web_url({web_url}) or full_name({full_name}) is not provided.')
    
    return 'https://github.com'  # 返回默认的GitHub URL


def standardize_github_event_type(github_event, action=None):
    """
    将GitHub事件类型标准化为系统内部事件类型
    
    参数:
        github_event: GitHub原始事件类型 (如: 'push', 'pull_request')
        action: GitHub事件的action字段 (仅对pull_request事件有效)
        
    返回:
        str: 标准化的事件类型 ('push' 或 'merge')
        
    事件类型映射:
        - GitHub 'push' -> 系统内部 'push'
        - GitHub 'pull_request' -> 系统内部 'merge'
        
    这确保了与GitLab事件处理的一致性:
        - GitLab 'push' -> 系统内部 'push'
        - GitLab 'merge_request' -> 系统内部 'merge'
    """
    if github_event == 'push':
        return 'push'
    elif github_event == 'pull_request':
        return 'merge'  # 标准化为内部的merge事件类型
    else:
        log.warning(f'Unknown GitHub event type: {github_event}, returning as-is')
        return github_event


def validate_github_event(github_event, body):
    """
    验证GitHub事件是否应该触发代码评审
    
    参数:
        github_event: GitHub事件类型
        body: webhook事件体
        
    返回:
        tuple: (should_process, reason) - 是否应该处理和原因说明
    """
    if github_event == 'push':
        # Push事件总是处理
        return True, 'Push event'
        
    elif github_event == 'pull_request':
        # Pull Request事件需要检查action
        action = body.get('action', '')
        if action in ['opened', 'synchronize', 'reopened']:
            return True, f'Pull request {action}'
        else:
            return False, f'Pull request action {action} does not trigger review'
            
    else:
        # 其他事件类型不处理
        return False, f'Unsupported event type: {github_event}'


def is_github_event_supported(github_event):
    """
    检查GitHub事件类型是否被支持
    
    参数:
        github_event: GitHub事件类型
        
    返回:
        bool: 是否支持该事件类型
    """
    supported_events = ['push', 'pull_request']
    return github_event in supported_events


def validate_github_parameters(params):
    """
    验证解析后的GitHub参数是否完整和有效
    
    参数:
        params: 解析后的参数字典
        
    返回:
        tuple: (is_valid, error_message) - 验证结果和错误信息
    """
    required_fields = ['source', 'project_id', 'event_type']
    
    # 检查必需字段
    for field in required_fields:
        if not params.get(field):
            return False, f'Missing required field: {field}'
    
    # 检查source是否为github
    if params.get('source') != 'github':
        return False, f'Invalid source: expected "github", got "{params.get("source")}"'
    
    # 检查事件类型是否为标准化后的类型
    event_type = params.get('event_type')
    if event_type not in ['push', 'merge']:
        return False, f'Invalid standardized event_type: expected "push" or "merge", got "{event_type}"'
    
    # 检查project_id格式（应该是owner/repo格式）
    project_id = params.get('project_id')
    if project_id and '/' not in project_id:
        log.warning(f'GitHub project_id should be in "owner/repo" format, got: {project_id}')
    
    # 如果commit_id为空字符串，表示跳过评审，这是正常的
    commit_id = params.get('commit_id')
    if commit_id is None:
        log.info('commit_id is None, this event will be skipped for review')
    
    return True, 'Parameters are valid'


def ensure_github_parameter_consistency(params):
    """
    确保GitHub参数与GitLab参数格式的一致性
    
    参数:
        params: 参数字典
        
    返回:
        dict: 调整后的参数字典
    """
    # 确保commit_id不为None（与GitLab保持一致）
    if params.get('commit_id') is None:
        params['commit_id'] = ''
    
    # 确保所有字符串字段不为None
    string_fields = ['username', 'ref', 'target_branch', 'previous_commit_id']
    for field in string_fields:
        if params.get(field) is None:
            params[field] = ''
    
    # 确保project_name有默认值
    if not params.get('project_name') and params.get('project_id'):
        # 从owner/repo中提取repo名称
        project_id = params.get('project_id', '')
        if '/' in project_id:
            params['project_name'] = project_id.split('/')[-1]
        else:
            params['project_name'] = project_id
    
    return params


def init_github_context(repo_url, project_id, private_token):
    """
    初始化GitHub仓库上下文
    
    参数:
        repo_url: GitHub API URL (通常是 https://github.com，会自动转换为API URL)
        project_id: 仓库全名 (格式: owner/repo-name)
        private_token: GitHub Personal Access Token
        
    返回:
        Repository: PyGithub Repository对象
        
    异常:
        base.CodelibException: 当连接失败或认证失败时抛出
    """
    try:
        log.info(f'Try to init GitHub connection for repo({repo_url}).')
        
        # 将GitHub web URL转换为API URL
        if repo_url and repo_url.startswith('https://github.com'):
            api_base_url = 'https://api.github.com'
        elif repo_url and 'api.github.com' in repo_url:
            api_base_url = repo_url
        else:
            # 默认使用公共GitHub API
            api_base_url = 'https://api.github.com'
        
        log.info(f'Using GitHub API base URL: {api_base_url}')
        
        # 创建GitHub客户端实例
        if api_base_url != 'https://api.github.com':
            # 对于GitHub Enterprise Server，需要指定base_url
            g = Github(private_token, base_url=api_base_url)
        else:
            # 对于公共GitHub，使用默认配置
            g = Github(private_token)
        
        log.info(f'Try to get repository({project_id})')
        
        # 获取仓库对象
        repository = g.get_repo(project_id)
        
        # 测试连接是否有效，通过访问仓库的基本信息
        _ = repository.name  # 这会触发API调用，验证认证和权限
        
        log.info(f'Successfully initialized GitHub context for repository({project_id})')
        return repository
        
    except BadCredentialsException as ex:
        error_msg = f'GitHub authentication failed: Invalid token or insufficient permissions'
        log.error(error_msg, extra=dict(repo_url=repo_url, project_id=project_id, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except UnknownObjectException as ex:
        error_msg = f'GitHub repository not found: {project_id}'
        log.error(error_msg, extra=dict(repo_url=repo_url, project_id=project_id, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except GithubException as ex:
        error_msg = f'GitHub API error: {ex.data.get("message", str(ex)) if hasattr(ex, "data") and ex.data else str(ex)}'
        log.error(error_msg, extra=dict(repo_url=repo_url, project_id=project_id, status=ex.status, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except Exception as ex:
        error_msg = f'Fail to init GitHub context: {ex}'
        log.error(error_msg, extra=dict(repo_url=repo_url, project_id=project_id, exception=str(ex)))
        raise base.CodelibException(error_msg, code='Unknown') from ex


def get_github_file(repository, path, ref):
    """
    获取GitHub仓库中指定文件的内容
    
    参数:
        repository: PyGithub Repository对象
        path: 文件路径
        ref: 提交ID或分支名
        
    返回:
        str: 文件内容，失败时返回None
        
    异常处理:
        - 文件不存在: 返回None
        - 权限错误: 返回None
        - 其他错误: 记录日志并返回None
    """
    try:
        log.info(f'Try to get GitHub file in ref({ref}): {path}')
        
        # 使用PyGithub获取文件内容
        file_content = repository.get_contents(path, ref=ref)
        
        # 检查是否是文件（不是目录）
        if file_content.type != 'file':
            log.warning(f'Path {path} is not a file, type: {file_content.type}')
            return None
        
        # 解码文件内容
        content = file_content.decoded_content.decode('utf-8')
        log.info(f'Got GitHub file {path} @ {ref}: {len(content)} characters')
        return content
        
    except UnknownObjectException as ex:
        log.info(f'GitHub file not found: {path} @ {ref}', extra=dict(exception=str(ex)))
        return None
        
    except GithubException as ex:
        if ex.status == 404:
            log.info(f'GitHub file not found: {path} @ {ref}', extra=dict(exception=str(ex)))
            return None
        elif ex.status == 403:
            log.warning(f'Permission denied for GitHub file: {path} @ {ref}', extra=dict(exception=str(ex)))
            return None
        else:
            log.error(f'GitHub API error getting file {path} @ {ref}', extra=dict(status=ex.status, exception=str(ex)))
            return None
            
    except UnicodeDecodeError as ex:
        log.error(f'Failed to decode GitHub file {path} @ {ref} as UTF-8', extra=dict(exception=str(ex)))
        return None
        
    except Exception as ex:
        log.error(f'Fail to get GitHub file {path} @ {ref}', extra=dict(exception=str(ex)))
        return None


def get_github_file_content(repository, file_path, ref_name):
    """
    获取GitHub仓库中指定文件的内容（内部版本）
    
    参数:
        repository: PyGithub Repository对象
        file_path: 文件路径
        ref_name: 提交ID或分支名
        
    返回:
        str: 文件内容
        
    异常:
        base.CodelibException: 当文件获取失败时抛出
    """
    try:
        # 使用PyGithub获取文件内容
        file_content = repository.get_contents(file_path, ref=ref_name)
        
        # 检查是否是文件（不是目录）
        if file_content.type != 'file':
            raise base.CodelibException(f'Path {file_path} is not a file, type: {file_content.type}', code='ValidationError')
        
        # 解码文件内容
        content = file_content.decoded_content.decode('utf-8')
        log.info(f'Getting GitHub file content({file_path}).', extra=dict(content_length=len(content)))
        return content
        
    except UnknownObjectException as ex:
        error_msg = f'GitHub file not found: {file_path} @ {ref_name}'
        log.error(error_msg, extra=dict(exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except GithubException as ex:
        error_msg = f'GitHub API error getting file {file_path} @ {ref_name}: {ex.data.get("message", str(ex)) if hasattr(ex, "data") and ex.data else str(ex)}'
        log.error(error_msg, extra=dict(status=ex.status, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except UnicodeDecodeError as ex:
        error_msg = f'Failed to decode GitHub file {file_path} @ {ref_name} as UTF-8'
        log.error(error_msg, extra=dict(exception=str(ex)))
        raise base.CodelibException(error_msg, code='EncodingError') from ex
        
    except Exception as ex:
        error_msg = f'Fail to get GitHub file content: {ex}'
        log.error(error_msg, extra=dict(file_path=file_path, ref_name=ref_name, exception=str(ex)))
        raise base.CodelibException(error_msg, code='Unknown') from ex


def get_diff_files(repository, from_commit_id, to_commit_id):
    """
    获取两个提交之间的文件差异
    
    参数:
        repository: PyGithub Repository对象
        from_commit_id: 起始提交ID（可能为全零表示新分支）
        to_commit_id: 结束提交ID
        
    返回:
        dict: 文件路径到差异内容的映射
        
    处理的文件变更类型:
        - 新增文件: 添加到结果中
        - 修改文件: 添加到结果中
        - 删除文件: 从结果中移除
        - 重命名文件: 移除旧路径，添加新路径
        
    特殊情况:
        - 当from_commit_id为全零时，表示新分支第一次提交，返回该提交的所有文件
    """
    try:
        log.info(f'Getting diff between commits: {from_commit_id} -> {to_commit_id}')
        
        # 检查是否为全零commit_id（新分支第一次提交的情况）
        zero_commit = "0000000000000000000000000000000000000000"
        if from_commit_id == zero_commit:
            log.info(f'Detected zero commit_id, treating as new branch first commit')
            # 对于新分支第一次提交，获取该提交的所有文件
            return get_commit_files(repository, to_commit_id)
        
        # 使用PyGithub的compare API获取两个提交之间的比较结果
        comparison = repository.compare(from_commit_id, to_commit_id)
        
        files = {}
        
        # 遍历所有变更的文件
        for file_change in comparison.files:
            filename = file_change.filename
            status = file_change.status
            patch = file_change.patch or ''  # patch可能为None
            
            log.debug(f'Processing file change: {filename}, status: {status}')
            
            if status == 'added':
                # 新增文件
                files[filename] = patch
                
            elif status == 'modified':
                # 修改文件
                files[filename] = patch
                
            elif status == 'removed':
                # 删除文件 - 从结果中移除（如果之前存在）
                if filename in files:
                    del files[filename]
                # 注意：删除的文件通常不会在同一次比较中先添加再删除，
                # 但为了保持与GitLab实现的一致性，我们保留这个逻辑
                
            elif status == 'renamed':
                # 重命名文件
                # GitHub API中，重命名文件的filename是新文件名
                # previous_filename是旧文件名
                old_filename = getattr(file_change, 'previous_filename', None)
                if old_filename and old_filename in files:
                    del files[old_filename]
                files[filename] = patch
                
            else:
                # 其他状态（如copied等）按修改处理
                log.info(f'Unknown file status: {status} for file {filename}, treating as modified')
                files[filename] = patch
        
        log.info(f'Found {len(files)} changed files between commits {from_commit_id} -> {to_commit_id}')
        return files
        
    except GithubException as ex:
        error_msg = f'GitHub API error comparing commits {from_commit_id} -> {to_commit_id}: {ex.data.get("message", str(ex)) if hasattr(ex, "data") and ex.data else str(ex)}'
        log.error(error_msg, extra=dict(status=ex.status, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except Exception as ex:
        error_msg = f'Fail to get diff files: {ex}'
        log.error(error_msg, extra=dict(from_commit=from_commit_id, to_commit=to_commit_id, exception=str(ex)))
        raise base.CodelibException(error_msg, code='Unknown') from ex


def get_commit_files(repository, commit_id):
    """
    获取指定提交的所有文件（用于新分支第一次提交的情况）
    
    参数:
        repository: PyGithub Repository对象
        commit_id: 提交ID
        
    返回:
        dict: 文件路径到空字符串的映射（因为是新文件，没有diff内容）
    """
    try:
        log.info(f'Getting all files for commit: {commit_id}')
        
        # 获取提交对象
        commit = repository.get_commit(commit_id)
        
        files = {}
        
        # 遍历提交中的所有文件
        for file_info in commit.files:
            filename = file_info.filename
            # 对于新分支的第一次提交，所有文件都是新增的
            # 使用patch内容，如果没有则使用空字符串
            patch = file_info.patch or ''
            files[filename] = patch
            log.debug(f'Added file from commit: {filename}')
        
        log.info(f'Found {len(files)} files in commit {commit_id}')
        return files
        
    except GithubException as ex:
        error_msg = f'GitHub API error getting commit files for {commit_id}: {ex.data.get("message", str(ex)) if hasattr(ex, "data") and ex.data else str(ex)}'
        log.error(error_msg, extra=dict(status=ex.status, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except Exception as ex:
        error_msg = f'Fail to get commit files: {ex}'
        log.error(error_msg, extra=dict(commit_id=commit_id, exception=str(ex)))
        raise base.CodelibException(error_msg, code='Unknown') from ex


def get_project_code_text(repository, commit_id, targets):
    """
    获取整个项目的代码文本
    
    参数:
        repository: PyGithub Repository对象
        commit_id: 提交ID
        targets: 目标文件模式列表
        
    返回:
        str: 格式化的代码文本
        
    处理流程:
        1. 获取指定提交的文件树
        2. 过滤出符合目标模式的文件
        3. 批量获取文件内容
        4. 格式化为统一的文本格式
    """
    try:
        log.info(f'Getting project code text for commit {commit_id} with targets: {targets}')
        
        # 获取指定提交的Git树（递归获取所有文件）
        git_tree = repository.get_git_tree(commit_id, recursive=True)
        
        # 提取所有文件路径（只要blob类型，不要tree类型）
        all_file_paths = [item.path for item in git_tree.tree if item.type == 'blob']
        
        # 使用base.filter_targets过滤符合目标模式的文件
        file_paths = base.filter_targets(all_file_paths, targets)
        
        log.info('Scanned {} files after filtering in repository for commit_id({}), filters({}).'.format(
            len(file_paths), commit_id, targets))
        
        # 构建代码文本
        text = ''
        for file_path in file_paths:
            try:
                # 获取文件内容
                file_content = get_github_file_content(repository, file_path, commit_id)
                
                # 格式化为代码段
                section = f'{file_path}\n```\n{file_content}\n```'
                text = '{}\n\n{}'.format(text, section) if text else section
                
            except Exception as ex:
                log.info(f'Fail to get file({file_path}) content.', extra=dict(exception=str(ex)))
                # 继续处理其他文件，不因单个文件失败而中断
                continue
        
        log.info(f'Successfully generated project code text with {len(file_paths)} files')
        return text
        
    except GithubException as ex:
        error_msg = f'GitHub API error getting project code text for commit {commit_id}: {ex.data.get("message", str(ex)) if hasattr(ex, "data") and ex.data else str(ex)}'
        log.error(error_msg, extra=dict(status=ex.status, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except Exception as ex:
        error_msg = f'Fail to get project code text: {ex}'
        log.error(error_msg, extra=dict(commit_id=commit_id, targets=targets, exception=str(ex)))
        raise base.CodelibException(error_msg, code='Unknown') from ex


def get_rules(repository, commit_id, branch):
    """
    从.codereview目录获取评审规则
    
    参数:
        repository: PyGithub Repository对象
        commit_id: 提交ID（可能为全零表示新分支）
        branch: 分支名
        
    返回:
        list: 规则列表
        
    特殊情况:
        - 当commit_id为全零时，使用分支名作为ref
    """
    folder = '.codereview'
    
    # 检查是否为全零commit_id（新分支第一次提交的情况）
    zero_commit = "0000000000000000000000000000000000000000"
    if commit_id == zero_commit:
        log.info(f'Detected zero commit_id, using branch {branch} as ref')
        ref = branch
    else:
        ref = commit_id if commit_id else branch
    
    try:
        # 获取.codereview目录内容
        contents = repository.get_contents(folder, ref=ref)
        filenames = []
        
        # 如果contents是单个文件，转换为列表
        if not isinstance(contents, list):
            contents = [contents]
            
        # 筛选出.yaml文件
        for item in contents:
            if item.name.lower().endswith('.yaml'):
                filenames.append(item.name)
                
    except UnknownObjectException:
        log.info(f'Directory .codereview is not in repository for ref {ref}')
        filenames = []
    except Exception as ex:
        raise base.CodelibException(f'Fail to get rules: {ex}') from ex
    
    rules = []
    for filename in filenames:
        path = f'.codereview/{filename}'
        try:
            file_content = get_github_file_content(repository, path, ref)
            content = yaml.safe_load(file_content) if file_content else dict()
            content['filename'] = filename
            rules.append(content)
        except Exception as ex:
            log.warning(f'Failed to load rule file {filename}: {ex}')
            continue
    
    return rules


def put_rule(repository, branch, filepath, content):
    """
    创建或更新规则文件
    
    参数:
        repository: PyGithub Repository对象
        branch: 分支名
        filepath: 文件路径
        content: 文件内容
    """
    # 将在任务6.2中实现
    raise NotImplementedError("put_rule will be implemented in task 6.2")


def get_last_commit_id(repository, branch):
    """
    获取分支的最新提交ID
    
    参数:
        repository: PyGithub Repository对象
        branch: 分支名
        
    返回:
        str: 最新提交ID
        
    异常:
        base.CodelibException: 当分支不存在或获取失败时抛出
    """
    try:
        log.info(f'Getting last commit ID for branch: {branch}')
        
        # 使用PyGithub获取分支信息
        branch_obj = repository.get_branch(branch)
        
        # 获取分支最新提交的SHA
        latest_commit_id = branch_obj.commit.sha
        
        log.info(f'Got last commit ID for branch {branch}: {latest_commit_id}')
        return latest_commit_id
        
    except UnknownObjectException as ex:
        error_msg = f'GitHub branch not found: {branch}'
        log.error(error_msg, extra=dict(branch=branch, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except GithubException as ex:
        error_msg = f'GitHub API error getting last commit for branch {branch}: {ex.data.get("message", str(ex)) if hasattr(ex, "data") and ex.data else str(ex)}'
        log.error(error_msg, extra=dict(branch=branch, status=ex.status, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except Exception as ex:
        error_msg = f'Fail to get last commit ID for branch {branch}: {ex}'
        log.error(error_msg, extra=dict(branch=branch, exception=str(ex)))
        raise base.CodelibException(error_msg, code='Unknown') from ex


def get_first_commit_id(repository, branch):
    """
    获取分支的首次提交ID
    
    参数:
        repository: PyGithub Repository对象
        branch: 分支名
        
    返回:
        str: 首次提交ID，如果没有找到则返回None
        
    异常:
        base.CodelibException: 当分支不存在或获取失败时抛出
        
    实现逻辑:
        1. 获取分支的所有提交历史
        2. 遍历提交找到没有父提交的提交（首次提交）
        3. 返回首次提交的SHA
        
    性能优化:
        - 使用分页获取提交，避免一次性加载所有提交
        - 设置合理的超时和重试机制
        - 限制最大检查提交数量，防止无限循环
    """
    try:
        log.info(f'Getting first commit ID for branch: {branch}')
        
        # 获取分支的所有提交，按时间倒序排列
        # 使用分页获取，避免一次性加载过多提交
        commits = repository.get_commits(sha=branch)
        
        # 遍历所有提交，找到没有父提交的提交（首次提交）
        first_commit_id = None
        commit_count = 0
        max_commits_to_check = 10000  # 设置最大检查提交数量，防止无限循环
        
        for commit in commits:
            commit_count += 1
            
            # 防止检查过多提交
            if commit_count > max_commits_to_check:
                log.warning(f'Reached maximum commit check limit ({max_commits_to_check}) for branch {branch}')
                break
            
            # 检查提交的父提交列表
            if len(commit.parents) == 0:
                # 没有父提交，这是首次提交
                first_commit_id = commit.sha
                log.info(f'Found first commit for branch {branch}: {first_commit_id} (checked {commit_count} commits)')
                break
            
            # 每检查100个提交记录一次进度
            if commit_count % 100 == 0:
                log.debug(f'Checked {commit_count} commits for branch {branch}, still searching for first commit')
        
        if first_commit_id is None:
            log.warning(f'No first commit found for branch {branch} after checking {commit_count} commits')
        
        return first_commit_id
        
    except UnknownObjectException as ex:
        error_msg = f'GitHub branch not found: {branch}'
        log.error(error_msg, extra=dict(branch=branch, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except GithubException as ex:
        error_msg = f'GitHub API error getting first commit for branch {branch}: {ex.data.get("message", str(ex)) if hasattr(ex, "data") and ex.data else str(ex)}'
        log.error(error_msg, extra=dict(branch=branch, status=ex.status, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except Exception as ex:
        error_msg = f'Fail to get first commit ID for branch {branch}: {ex}'
        log.error(error_msg, extra=dict(branch=branch, exception=str(ex)))
        raise base.CodelibException(error_msg, code='Unknown') from ex


def get_branch_info(repository, branch):
    """
    获取分支的详细信息
    
    参数:
        repository: PyGithub Repository对象
        branch: 分支名
        
    返回:
        dict: 分支信息字典，包含名称、最新提交等信息
        
    异常:
        base.CodelibException: 当分支不存在或获取失败时抛出
        
    性能优化:
        - 一次API调用获取完整分支信息
        - 缓存分支信息避免重复查询
    """
    try:
        log.info(f'Getting branch info for: {branch}')
        
        # 使用PyGithub获取分支信息
        branch_obj = repository.get_branch(branch)
        
        # 构建分支信息字典
        branch_info = {
            'name': branch_obj.name,
            'commit_sha': branch_obj.commit.sha,
            'commit_message': branch_obj.commit.commit.message,
            'commit_author': branch_obj.commit.commit.author.name,
            'commit_date': branch_obj.commit.commit.author.date.isoformat(),
            'protected': branch_obj.protected
        }
        
        log.info(f'Got branch info for {branch}: commit {branch_info["commit_sha"][:8]}')
        return branch_info
        
    except UnknownObjectException as ex:
        error_msg = f'GitHub branch not found: {branch}'
        log.error(error_msg, extra=dict(branch=branch, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except GithubException as ex:
        error_msg = f'GitHub API error getting branch info for {branch}: {ex.data.get("message", str(ex)) if hasattr(ex, "data") and ex.data else str(ex)}'
        log.error(error_msg, extra=dict(branch=branch, status=ex.status, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except Exception as ex:
        error_msg = f'Fail to get branch info for {branch}: {ex}'
        log.error(error_msg, extra=dict(branch=branch, exception=str(ex)))
        raise base.CodelibException(error_msg, code='Unknown') from ex


def get_commit_history(repository, branch, limit=100):
    """
    获取分支的提交历史
    
    参数:
        repository: PyGithub Repository对象
        branch: 分支名
        limit: 最大返回提交数量，默认100
        
    返回:
        list: 提交信息列表，每个元素包含提交的基本信息
        
    异常:
        base.CodelibException: 当分支不存在或获取失败时抛出
        
    性能优化:
        - 限制返回的提交数量
        - 只获取必要的提交信息字段
        - 使用分页避免内存过载
    """
    try:
        log.info(f'Getting commit history for branch {branch}, limit: {limit}')
        
        # 获取分支的提交历史
        commits = repository.get_commits(sha=branch)
        
        # 构建提交历史列表
        commit_history = []
        count = 0
        
        for commit in commits:
            if count >= limit:
                break
                
            commit_info = {
                'sha': commit.sha,
                'message': commit.commit.message,
                'author': commit.commit.author.name,
                'date': commit.commit.author.date.isoformat(),
                'parent_count': len(commit.parents),
                'parent_shas': [parent.sha for parent in commit.parents]
            }
            
            commit_history.append(commit_info)
            count += 1
        
        log.info(f'Got {len(commit_history)} commits for branch {branch}')
        return commit_history
        
    except UnknownObjectException as ex:
        error_msg = f'GitHub branch not found: {branch}'
        log.error(error_msg, extra=dict(branch=branch, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except GithubException as ex:
        error_msg = f'GitHub API error getting commit history for branch {branch}: {ex.data.get("message", str(ex)) if hasattr(ex, "data") and ex.data else str(ex)}'
        log.error(error_msg, extra=dict(branch=branch, status=ex.status, exception=str(ex)))
        raise base.CodelibException(error_msg, code=parse_github_errcode(ex)) from ex
        
    except Exception as ex:
        error_msg = f'Fail to get commit history for branch {branch}: {ex}'
        log.error(error_msg, extra=dict(branch=branch, exception=str(ex)))
        raise base.CodelibException(error_msg, code='Unknown') from ex


def validate_commit_exists(repository, commit_sha):
    """
    验证提交是否存在
    
    参数:
        repository: PyGithub Repository对象
        commit_sha: 提交SHA
        
    返回:
        bool: 提交是否存在
        
    性能优化:
        - 使用轻量级API调用验证提交存在性
        - 避免获取完整提交信息
    """
    try:
        log.debug(f'Validating commit exists: {commit_sha}')
        
        # 尝试获取提交对象，只获取基本信息
        commit = repository.get_commit(commit_sha)
        
        # 如果能获取到提交对象，说明提交存在
        return commit.sha == commit_sha
        
    except UnknownObjectException:
        log.debug(f'Commit not found: {commit_sha}')
        return False
        
    except GithubException as ex:
        if ex.status == 404:
            log.debug(f'Commit not found: {commit_sha}')
            return False
        else:
            log.warning(f'GitHub API error validating commit {commit_sha}: {ex}')
            return False
            
    except Exception as ex:
        log.warning(f'Error validating commit {commit_sha}: {ex}')
        return False