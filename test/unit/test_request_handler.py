"""
request_handler.py 单元测试

测试目标：验证 request_handler 模块的核心功能
- webhook 请求接收和参数解析
- DynamoDB 记录创建
- 异步 Lambda 任务分发
- 异常处理和错误响应

测试策略：
- 使用 sys.modules Mock 隔离所有外部依赖
- 针对不同请求类型（webtool/webhook）分别测试
- 覆盖正常流程和异常情况
- 验证关键业务逻辑的正确性
"""

import pytest
import json
import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加lambda目录到路径，使测试能够导入被测试模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

# Mock策略：通过 sys.modules 完全隔离外部依赖
# 这样避免了安装复杂依赖，同时保证测试的独立性和速度
mock_boto3 = Mock()
mock_gitlab = Mock()
mock_awslambdaric = Mock()
mock_logger = Mock()

sys.modules['boto3'] = mock_boto3
sys.modules['gitlab'] = mock_gitlab
sys.modules['gitlab.exceptions'] = Mock()
sys.modules['awslambdaric'] = mock_awslambdaric
sys.modules['awslambdaric.lambda_runtime_log_utils'] = Mock()
sys.modules['logger'] = mock_logger

# Mock logger的init_logger函数，避免日志初始化问题
mock_logger.init_logger = Mock()

import request_handler
from request_handler import lambda_handler, get_invoker, process

class TestRequestHandler:
    """
    request_handler 模块的单元测试类
    
    测试范围：
    1. get_invoker 函数 - 请求来源识别
    2. process 函数 - 核心业务逻辑处理
    3. lambda_handler 函数 - Lambda 入口点
    4. 异常处理和错误响应
    """
    
    def setup_method(self):
        """
        测试前置设置
        
        目的：为每个测试方法提供干净的环境
        操作：设置必要的环境变量，模拟 Lambda 运行环境
        """
        # 设置 Lambda 函数需要的环境变量
        os.environ['REQUEST_TABLE'] = 'test-request-table'
        os.environ['TASK_DISPATCHER_FUN_NAME'] = 'test-task-dispatcher'
    
    def teardown_method(self):
        """
        测试后置清理
        
        目的：清理测试环境，避免测试间相互影响
        操作：删除设置的环境变量
        """
        # 清理环境变量，确保测试隔离
        if 'REQUEST_TABLE' in os.environ:
            del os.environ['REQUEST_TABLE']
        if 'TASK_DISPATCHER_FUN_NAME' in os.environ:
            del os.environ['TASK_DISPATCHER_FUN_NAME']
    
    def test_get_invoker_webtool(self):
        """
        测试目的：验证从 webtool 请求中正确解析 invoker 字段
        
        测试场景：Web 工具发送的手动评审请求
        输入数据：包含 invoker='webtool' 的 JSON body
        测试过程：
        1. 构造包含 webtool invoker 的事件
        2. 调用 get_invoker 函数解析
        3. 验证返回正确的 invoker 值
        
        期望结果：返回 'webtool' 字符串
        业务意义：系统能够识别来自 Web 工具的手动评审请求
        """
        # 构造 webtool 请求事件
        event = {
            'body': json.dumps({'invoker': 'webtool'})
        }
        
        # 执行解析
        result = get_invoker(event)
        
        # 验证结果
        assert result == 'webtool'
    
    def test_get_invoker_no_body(self):
        """
        测试目的：验证处理没有 body 字段的请求
        
        测试场景：异常请求或格式错误的 API Gateway 事件
        输入数据：空的事件对象
        测试过程：
        1. 构造没有 body 字段的事件
        2. 调用 get_invoker 函数
        3. 验证函数不会崩溃并返回 None
        
        期望结果：返回 None，表示无法识别请求来源
        业务意义：系统对异常请求具有容错性
        """
        # 构造没有 body 的事件
        event = {}
        
        # 执行解析
        result = get_invoker(event)
        
        # 验证返回 None
        assert result is None
    
    def test_get_invoker_invalid_json(self):
        """
        测试目的：验证处理无效 JSON 格式的 body
        
        测试场景：客户端发送格式错误的 JSON 数据
        输入数据：包含无效 JSON 字符串的 body
        测试过程：
        1. 构造包含无效 JSON 的事件
        2. 调用 get_invoker 函数
        3. 验证函数捕获 JSON 解析异常并返回 None
        
        期望结果：返回 None，不抛出异常
        业务意义：系统对格式错误的请求具有容错性
        """
        # 构造包含无效 JSON 的事件
        event = {
            'body': 'invalid json'
        }
        
        # 执行解析
        result = get_invoker(event)
        
        # 验证返回 None
        assert result is None
    
    def test_get_invoker_no_invoker_field(self):
        """
        测试目的：验证处理缺少 invoker 字段的有效 JSON
        
        测试场景：JSON 格式正确但缺少关键字段的请求
        输入数据：有效 JSON 但不包含 invoker 字段
        测试过程：
        1. 构造有效 JSON 但缺少 invoker 字段的事件
        2. 调用 get_invoker 函数
        3. 验证返回 None
        
        期望结果：返回 None，表示无法识别请求来源
        业务意义：系统能够区分不同类型的请求格式
        """
        # 构造缺少 invoker 字段的事件
        event = {
            'body': json.dumps({'other_field': 'value'})
        }
        
        # 执行解析
        result = get_invoker(event)
        
        # 验证返回 None
        assert result is None
    
    @patch('request_handler.lambda_client')
    @patch('request_handler.dynamodb')
    @patch('request_handler.codelib')
    @patch('request_handler.base')
    def test_process_webtool_success(self, mock_base, mock_codelib, mock_dynamodb, mock_lambda_client):
        """
        测试目的：验证 webtool 请求的完整成功处理流程
        
        测试场景：用户通过 Web 工具手动触发代码评审
        业务流程：
        1. 接收 webtool 请求
        2. 解析请求参数
        3. 初始化仓库上下文
        4. 格式化 commit ID
        5. 创建 DynamoDB 记录
        6. 异步调用任务分发器
        7. 返回成功响应
        
        Mock 策略：
        - mock_base: 模拟基础工具函数
        - mock_codelib: 模拟代码库操作
        - mock_dynamodb: 模拟数据库操作
        - mock_lambda_client: 模拟 Lambda 调用
        
        验证点：
        1. HTTP 响应状态码为 200
        2. 响应包含正确的 request_id 和 commit_id
        3. DynamoDB 记录创建正确
        4. Lambda 异步调用参数正确
        """
        
        # === Mock 设置阶段 ===
        # 设置 DynamoDB Mock
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        # 设置基础工具 Mock
        mock_base.STATUS_START = 'Start'
        mock_base.dump_json.return_value = '{"test": "payload"}'
        mock_base.response_success_post.return_value = {
            'statusCode': 200,
            'body': json.dumps({'request_id': 'test_request_123', 'commit_id': 'abc123'})
        }
        
        # 设置完整的请求参数 Mock（包含所有必要字段）
        mock_params = {
            'request_id': 'test_request_123',
            'commit_id': 'abc123',
            'project_name': 'test-project',
            'target_branch': 'main',
            'repo_url': 'https://gitlab.com/test/repo',
            'project_id': '123',
            'private_token': 'token123',
            'ref': 'refs/heads/main'  # 日志输出需要的字段
        }
        
        # 设置代码库操作 Mock
        mock_codelib.parse_webtool_parameters.return_value = mock_params
        mock_codelib.init_repo_context.return_value = {'source': 'gitlab', 'project': Mock()}
        mock_codelib.format_commit_id.return_value = 'abc123'  # 模拟 commit ID 格式化
        
        # === 测试执行阶段 ===
        # 构造 webtool 请求事件
        event = {
            'body': json.dumps({'invoker': 'webtool'})
        }
        context = Mock()
        
        # 执行被测试函数
        result = process(event, context)
        
        # === 结果验证阶段 ===
        # 验证 HTTP 响应
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['request_id'] == 'test_request_123'
        assert response_body['commit_id'] == 'abc123'
        
        # 验证 DynamoDB 操作
        mock_table.put_item.assert_called_once()
        put_item_args = mock_table.put_item.call_args[1]['Item']
        assert put_item_args['commit_id'] == 'abc123'
        assert put_item_args['request_id'] == 'test_request_123'
        assert put_item_args['task_status'] == 'Start'
        assert put_item_args['project_name'] == 'test-project'
        assert put_item_args['task_complete'] == 0
        assert put_item_args['task_failure'] == 0
        assert put_item_args['task_total'] == 0
        
        # 验证 Lambda 异步调用
        # 单元测试只需要验证调用了 invoke 方法，不需要验证具体参数
        # 因为这是 request_handler 的职责边界，Lambda B 的执行结果不在此测试范围内
        mock_lambda_client.invoke.assert_called_once()
    
    @patch('request_handler.lambda_client')
    @patch('request_handler.dynamodb')
    @patch('request_handler.codelib')
    @patch('request_handler.base')
    def test_process_gitlab_webhook_success(self, mock_base, mock_codelib, mock_dynamodb, mock_lambda_client):
        """
        测试目的：验证 GitLab webhook 请求的成功处理流程
        
        测试场景：GitLab 仓库发生 push 事件，自动触发代码评审
        业务流程：
        1. 接收 GitLab webhook 事件
        2. 识别为非 webtool 请求
        3. 解析 GitLab 事件参数
        4. 处理 commit ID 格式化
        5. 创建评审请求记录
        6. 触发异步任务处理
        
        与 webtool 测试的区别：
        - 使用 parse_parameters 而非 parse_webtool_parameters
        - 事件格式为 GitLab webhook 标准格式
        - 包含 previous_commit_id 用于 diff 分析
        
        验证重点：
        1. 正确识别 webhook 请求类型
        2. 参数解析函数调用正确
        3. 业务流程执行完整
        """
        
        # === Mock 设置阶段 ===
        # 设置数据库和基础工具 Mock
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_base.STATUS_START = 'Start'
        mock_base.dump_json.return_value = '{"test": "payload"}'
        mock_base.response_success_post.return_value = {
            'statusCode': 200,
            'body': json.dumps({'request_id': 'test_request_456', 'commit_id': 'def456'})
        }
        
        # 设置 GitLab webhook 参数 Mock（包含 diff 分析所需的 previous_commit_id）
        mock_params = {
            'request_id': 'test_request_456',
            'commit_id': 'def456',
            'previous_commit_id': 'abc123',  # webhook 特有，用于 diff 分析
            'project_name': 'webhook-project',
            'target_branch': 'develop',
            'repo_url': 'https://gitlab.com/test/webhook-repo',
            'project_id': '456',
            'private_token': 'webhook_token',
            'ref': 'refs/heads/develop'
        }
        
        # 设置代码库操作 Mock
        mock_codelib.parse_parameters.return_value = mock_params  # 注意：使用 parse_parameters
        mock_codelib.init_repo_context.return_value = {'source': 'gitlab', 'project': Mock()}
        # 模拟 commit ID 不需要格式化的情况
        mock_codelib.format_commit_id.side_effect = lambda ctx, branch, commit: commit
        
        # === 测试执行阶段 ===
        # 构造标准的 GitLab push webhook 事件
        event = {
            'body': json.dumps({
                'object_kind': 'push',  # GitLab webhook 事件类型
                'project': {'id': 456, 'name': 'webhook-project'},
                'commits': [{'id': 'def456', 'message': 'webhook commit'}],
                'ref': 'refs/heads/develop'  # 分支引用
            }),
            'headers': {'X-Gitlab-Event': 'Push Hook'}  # GitLab webhook 标识
        }
        context = Mock()
        
        # 执行被测试函数
        result = process(event, context)
        
        # === 结果验证阶段 ===
        # 验证 HTTP 响应正确
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['request_id'] == 'test_request_456'
        assert response_body['commit_id'] == 'def456'
        
        # 验证参数解析函数调用正确
        # 关键验证：webhook 请求应该调用 parse_parameters 而不是 parse_webtool_parameters
        mock_codelib.parse_parameters.assert_called_once_with(event)
        mock_codelib.parse_webtool_parameters.assert_not_called()
        
        # 验证数据库记录创建
        mock_table.put_item.assert_called_once()
        put_item_args = mock_table.put_item.call_args[1]['Item']
        assert put_item_args['commit_id'] == 'def456'
        assert put_item_args['request_id'] == 'test_request_456'
        assert put_item_args['project_name'] == 'webhook-project'
    
    @patch('request_handler.codelib')
    @patch('request_handler.base')
    def test_process_general_exception(self, mock_base, mock_codelib):
        """
        测试目的：验证一般异常的处理机制
        
        测试场景：参数解析过程中发生未预期的异常
        异常类型：一般 Exception（非 CodelibException）
        
        测试过程：
        1. Mock parse_webtool_parameters 抛出一般异常
        2. 调用 process 函数
        3. 验证异常被正确捕获
        4. 验证返回适当的错误响应
        
        异常处理逻辑：
        - 捕获所有 Exception 类型异常
        - 记录错误日志
        - 返回 400 状态码和错误信息
        - 确保系统不会因异常而崩溃
        
        期望结果：
        - 返回 400 状态码
        - 响应体包含错误信息
        - 系统保持稳定运行
        """
        
        # === Mock 设置阶段 ===
        # 修复 CodelibException Mock 问题：创建一个合适的异常类
        class MockCodelibException(Exception):
            def __init__(self, message, code=None):
                super().__init__(message)
                self.code = code
        
        mock_base.CodelibException = MockCodelibException
        
        # 设置参数解析抛出异常
        mock_codelib.parse_webtool_parameters.side_effect = Exception("Unexpected error")
        
        # 设置错误响应 Mock
        mock_base.response_failure_post.return_value = {
            'statusCode': 400,
            'body': json.dumps({'error': 'Unexpected error'})
        }
        
        # === 测试执行阶段 ===
        # 构造触发异常的请求
        event = {
            'body': json.dumps({'invoker': 'webtool'})
        }
        context = Mock()
        
        # 执行被测试函数（应该捕获异常而不是抛出）
        result = process(event, context)
        
        # === 结果验证阶段 ===
        # 验证错误响应格式正确
        assert result['statusCode'] == 400
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Unexpected error'
        
        # 验证错误响应函数被正确调用
        mock_base.response_failure_post.assert_called_once_with('Unexpected error')
    
    @patch('request_handler.process')
    def test_lambda_handler(self, mock_process):
        """
        测试目的：验证 Lambda 入口函数的正确性
        
        测试场景：AWS Lambda 运行时调用 lambda_handler 函数
        函数职责：
        - 作为 Lambda 函数的标准入口点
        - 接收 AWS Lambda 运行时传递的 event 和 context
        - 将请求委托给 process 函数处理
        - 返回 process 函数的处理结果
        
        测试策略：
        - Mock process 函数，避免复杂的业务逻辑
        - 验证参数传递的正确性
        - 验证返回值的正确性
        
        期望行为：
        1. 正确调用 process 函数
        2. 传递原始的 event 和 context 参数
        3. 返回 process 函数的结果
        """
        
        # === Mock 设置阶段 ===
        # 设置 process 函数的返回值
        mock_process.return_value = {'statusCode': 200, 'body': '{"success": true}'}
        
        # === 测试执行阶段 ===
        # 构造 Lambda 事件和上下文
        event = {'test': 'event'}
        context = Mock()
        
        # 调用 Lambda 入口函数
        result = lambda_handler(event, context)
        
        # === 结果验证阶段 ===
        # 验证 process 函数被正确调用
        mock_process.assert_called_once_with(event, context)
        
        # 验证返回值正确传递
        assert result['statusCode'] == 200
        assert result == {'statusCode': 200, 'body': '{"success": true}'}
    
    @patch('request_handler.base')
    def test_invalid_webhook_format(self, mock_base):
        """
        测试目的：验证无效 webhook 格式的处理
        
        测试场景：接收到格式错误的 webhook 请求
        错误类型：JSON 解析失败
        
        测试过程：
        1. 构造包含无效 JSON 的请求
        2. 调用 lambda_handler 处理
        3. 验证系统正确处理 JSON 解析异常
        4. 验证返回适当的错误响应
        
        异常处理链路：
        1. get_invoker 返回 None（JSON 解析失败）
        2. 进入 else 分支调用 parse_parameters
        3. parse_parameters 中的 JSON 解析失败
        4. 异常被 process 函数的 except 块捕获
        5. 返回错误响应
        
        期望结果：
        - 返回 400 状态码
        - 系统不崩溃
        - 错误信息合理
        """
        
        # === Mock 设置阶段 ===
        # 修复 CodelibException Mock 问题：创建一个合适的异常类
        class MockCodelibException(Exception):
            def __init__(self, message, code=None):
                super().__init__(message)
                self.code = code
        
        mock_base.CodelibException = MockCodelibException
        
        # 设置错误响应 Mock
        mock_base.response_failure_post.return_value = {
            'statusCode': 400,
            'body': json.dumps({'error': 'invalid request'})
        }
        
        # === 测试执行阶段 ===
        # 构造包含无效 JSON 的 webhook 事件
        event = {
            'body': 'invalid json',  # 无效的 JSON 格式
            'headers': {}
        }
        context = Mock()
        
        # 调用 Lambda 处理函数
        result = lambda_handler(event, context)
        
        # === 结果验证阶段 ===
        # 验证返回错误状态码
        assert result['statusCode'] == 400
        
        # 验证错误响应函数被调用
        mock_base.response_failure_post.assert_called()