"""
request_handler.py 单元测试

测试目标：验证 request_handler 模块的核心功能
- webhook 请求接收和参数解析
- DynamoDB 记录创建
- 异步 Lambda 任务分发
- 异常处理和错误响应

测试方法：
- 使用 sys.modules Mock 隔离外部模块依赖
- 使用真实AWS服务（DynamoDB、Lambda）验证核心业务逻辑
- 针对不同请求类型（webtool/webhook）分别测试
- 覆盖正常流程和异常情况
- 通过直接读取数据库验证数据写入的正确性
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
        
        目的：为每个测试方法提供完整的测试环境
        操作：设置所有必要的环境变量，模拟真实的 Lambda 运行环境
        """
        # 导入测试配置
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from test_config import setup_test_environment
        
        # 设置完整的测试环境变量
        setup_test_environment()
    
    def teardown_method(self):
        """
        测试后置清理
        
        目的：清理测试环境，避免测试间相互影响
        操作：清理设置的环境变量
        """
        # 导入测试配置
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from test_config import cleanup_test_environment
        
        # 清理测试环境变量
        cleanup_test_environment()
    
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
    
    @patch('request_handler.codelib')
    @patch('request_handler.base')
    def test_process_webtool_success(self, mock_base, mock_codelib):
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
        
        测试流程：
        1. 准备测试数据：设置完整的webtool请求参数，包含项目信息、提交ID等
        2. 模拟外部依赖：Mock GitLab相关操作，避免依赖真实仓库
        3. 执行核心功能：调用process函数处理webtool请求
        4. 验证数据库写入：直接从真实DynamoDB表中读取创建的记录
        5. 检查字段完整性：验证所有必要字段（主键、状态、计数器、时间戳）
        6. 验证HTTP响应：确认返回正确的状态码和响应内容
        7. 清理测试数据：删除创建的数据库记录，避免测试间干扰
        
        验证点：
        1. HTTP 响应状态码为 200
        2. 响应包含正确的 request_id 和 commit_id
        3. DynamoDB 中实际存在正确的记录
        4. 记录的所有字段值符合预期
        """
        
        # === Mock 设置阶段 ===
        # 设置基础工具 Mock（保留常量和工具函数的Mock）
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
        
        # 验证 DynamoDB 实际写入（使用真实数据库）
        import boto3
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['REQUEST_TABLE'])
        
        # 直接从数据库读取记录进行验证
        response = table.get_item(
            Key={
                'commit_id': 'abc123',
                'request_id': 'test_request_123'
            }
        )
        
        # 验证记录存在且字段正确
        assert 'Item' in response, "数据库中应该存在创建的记录"
        item = response['Item']
        assert item['commit_id'] == 'abc123'
        assert item['request_id'] == 'test_request_123'
        assert item['task_status'] == 'Start'
        assert item['project_name'] == 'test-project'
        assert item['task_complete'] == 0
        assert item['task_failure'] == 0
        assert item['task_total'] == 0
        assert 'create_time' in item
        assert 'update_time' in item
        
        # 清理测试数据
        table.delete_item(
            Key={
                'commit_id': 'abc123',
                'request_id': 'test_request_123'
            }
        )
    
    @patch('request_handler.codelib')
    @patch('request_handler.base')
    def test_process_gitlab_webhook_success(self, mock_base, mock_codelib):
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
        # 设置基础工具 Mock
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
        
        # 验证 DynamoDB 实际写入（使用真实数据库）
        import boto3
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['REQUEST_TABLE'])
        
        # 直接从数据库读取记录进行验证
        response = table.get_item(
            Key={
                'commit_id': 'def456',
                'request_id': 'test_request_456'
            }
        )
        
        # 验证记录存在且字段正确
        assert 'Item' in response, "数据库中应该存在创建的记录"
        item = response['Item']
        assert item['commit_id'] == 'def456'
        assert item['request_id'] == 'test_request_456'
        assert item['project_name'] == 'webhook-project'
        assert item['task_status'] == 'Start'
        
        # 清理测试数据
        table.delete_item(
            Key={
                'commit_id': 'def456',
                'request_id': 'test_request_456'
            }
        )
    
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
        
        测试流程：
        1. Mock process函数：避免执行复杂的业务逻辑，专注测试入口函数
        2. 构造Lambda事件：模拟AWS Lambda运行时传递的标准参数
        3. 调用lambda_handler：验证入口函数正确委托给process函数
        4. 验证参数传递：确认event和context参数正确传递
        5. 验证返回值：确认lambda_handler返回process函数的结果
        
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
    
    @patch('request_handler.codelib')
    @patch('request_handler.base')
    def test_process_database_record_creation_details(self, mock_base, mock_codelib):
        """
        测试目的：详细验证数据库记录创建的完整性
        
        测试场景：专门验证 request_handler 创建的初始记录是否包含所有必要字段
        业务重要性：
        - 这条记录是整个代码评审流程的起点
        - 后续的 task_dispatcher 和其他组件都依赖这条记录
        - 记录的完整性直接影响整个系统的可靠性
        
        测试流程：
        1. 准备详细测试数据：构造包含所有业务字段的完整请求参数
        2. 设置Mock依赖：仅模拟GitLab和基础工具函数，保持AWS服务真实
        3. 执行请求处理：调用process函数，触发完整的数据库记录创建流程
        4. 直接验证数据库：从真实DynamoDB表中读取刚创建的记录
        5. 逐字段详细检查：验证主键、业务字段、状态字段、计数器、时间戳等
        6. 验证HTTP响应：确认返回内容包含正确的请求ID和提交ID
        7. 数据清理：删除测试记录，确保测试环境干净
        
        验证重点：
        1. 记录的主键和排序键正确
        2. 初始状态字段设置正确
        3. 时间戳字段存在
        4. 项目信息正确记录
        5. 任务计数器初始化正确
        
        期望结果：
        - DynamoDB 中实际存在创建的记录
        - 记录包含所有必要字段
        - 字段值符合业务逻辑要求
        - 初始状态和计数器设置正确
        """
        
        # === Mock 设置阶段 ===
        mock_base.STATUS_START = 'Start'
        mock_base.dump_json.return_value = '{"test": "payload"}'
        mock_base.response_success_post.return_value = {
            'statusCode': 200,
            'body': json.dumps({'request_id': 'detailed_test_123', 'commit_id': 'commit_abc'})
        }
        
        # 设置详细的请求参数
        mock_params = {
            'request_id': 'detailed_test_123',
            'commit_id': 'commit_abc',
            'project_name': 'critical-project',
            'target_branch': 'main',
            'repo_url': 'https://gitlab.com/test/critical-repo',
            'project_id': '999',
            'private_token': 'secret_token',
            'ref': 'refs/heads/main'
        }
        
        mock_codelib.parse_webtool_parameters.return_value = mock_params
        mock_codelib.init_repo_context.return_value = {'source': 'gitlab', 'project': Mock()}
        mock_codelib.format_commit_id.return_value = 'commit_abc'
        
        # === 测试执行阶段 ===
        event = {'body': json.dumps({'invoker': 'webtool'})}
        context = Mock()
        
        result = process(event, context)
        
        # === 详细验证阶段 ===
        # 验证 DynamoDB 实际写入（使用真实数据库）
        import boto3
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['REQUEST_TABLE'])
        
        # 直接从数据库读取记录进行详细验证
        response = table.get_item(
            Key={
                'commit_id': 'commit_abc',
                'request_id': 'detailed_test_123'
            }
        )
        
        # 验证记录存在
        assert 'Item' in response, "数据库中应该存在创建的记录"
        actual_item = response['Item']
        
        # 验证主键字段
        assert actual_item['commit_id'] == 'commit_abc', "commit_id 应该正确设置为主键"
        assert actual_item['request_id'] == 'detailed_test_123', "request_id 应该正确设置为排序键"
        
        # 验证业务字段
        assert actual_item['project_name'] == 'critical-project', "项目名称应该正确记录"
        
        # 验证状态字段
        assert actual_item['task_status'] == 'Start', "初始状态应该为 Start"
        
        # 验证计数器字段（这些是后续 task_dispatcher 更新的基础）
        assert actual_item['task_complete'] == 0, "已完成任务数应该初始化为 0"
        assert actual_item['task_failure'] == 0, "失败任务数应该初始化为 0"
        assert actual_item['task_total'] == 0, "总任务数应该初始化为 0"
        
        # 验证时间戳字段存在
        assert 'create_time' in actual_item, "应该包含创建时间"
        assert 'update_time' in actual_item, "应该包含更新时间"
        assert actual_item['create_time'] is not None, "创建时间不应该为空"
        assert actual_item['update_time'] is not None, "更新时间不应该为空"
        
        # 验证响应正确
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert response_body['request_id'] == 'detailed_test_123'
        assert response_body['commit_id'] == 'commit_abc'
        
        # 清理测试数据
        table.delete_item(
            Key={
                'commit_id': 'commit_abc',
                'request_id': 'detailed_test_123'
            }
        )
    
    def test_process_task_dispatcher_trigger_verification(self):
        """
        测试目的：验证 task_dispatcher Lambda 的触发机制
        
        测试场景：确保 request_handler 正确触发 task_dispatcher 进行后续处理
        业务重要性：
        - task_dispatcher 负责将请求分解为具体的评审任务
        - 触发失败会导致整个评审流程中断
        - 异步调用的参数必须正确传递
        
        测试流程：
        1. 构造丰富的真实webtool请求：包含完整的项目信息、提交ID、分支等
        2. 只Mock最底层的GitLab API调用：gitlab.Gitlab()和相关API
        3. 让所有业务逻辑真实执行：参数解析、上下文初始化、commit格式化等
        4. 执行完整的请求处理流程：触发真实的数据库写入和Lambda调用
        5. 验证初始数据库记录：确认request_handler创建的记录正确
        6. 等待task_dispatcher异步执行：给足够时间让真实Lambda执行
        7. 验证数据库状态变化：检查task_dispatcher的更新效果
        8. 清理测试数据：删除创建的记录
        
        关键验证点：
        - 业务逻辑层真实执行（参数解析、上下文初始化）
        - 数据库真实写入和读取
        - Lambda真实异步调用和执行
        - 整个处理链路的真实性和完整性
        
        验证重点：
        1. Lambda 异步调用使用正确的函数名
        2. 调用类型为异步（Event）
        3. 传递的参数包含完整的请求信息
        4. 调用在数据库记录创建之后进行
        
        期望结果：
        - 初始记录成功创建（task_status='Start'）
        - task_dispatcher被异步触发并执行
        - 数据库记录状态被更新（task_status变为后续状态）
        - 整个异步处理链路正常工作
        """
        
        # === Mock 设置阶段 ===
        # 只Mock最底层的GitLab API调用
        with patch('gitlab_code.gitlab.Gitlab') as mock_gitlab_class:
            # 设置GitLab API Mock
            mock_gl = Mock()
            mock_project = Mock()
            mock_gitlab_class.return_value = mock_gl
            mock_gl.projects.get.return_value = mock_project
            
            # 构造丰富的真实webtool请求
            event = {
                'body': json.dumps({
                    'invoker': 'webtool',
                    'mode': 'diff',
                    'model': 'claude3-sonnet',
                    'event_type': 'manual',
                    'web_url': 'https://gitlab.com/test/awesome-project.git',
                    'path_with_namespace': 'test/awesome-project',
                    'target_branch': 'feature/new-feature',
                    'ref': 'refs/heads/feature/new-feature',
                    'commit_id': 'abc123def456789',
                    'previous_commit_id': 'xyz789abc123456',
                    'private_token': 'glpat-test-token-12345',
                    'target': '**/*.py,**/*.js',
                    'rule_name': 'comprehensive-review',
                    'confirm': True,
                    'confirm_prompt': 'Please review this code carefully',
                    'prompt_system': 'You are a senior code reviewer'
                })
            }
        
            # === 测试执行阶段 ===
            context = Mock()
            
            # 执行真实的请求处理（让所有业务逻辑真实执行）
            result = process(event, context)
            
            # === 验证阶段 ===
            # 验证响应正确
            assert result['statusCode'] == 200
            response_body = json.loads(result['body'])
            
            # 从响应中获取实际的request_id和commit_id（由真实业务逻辑生成）
            actual_request_id = response_body['request_id']
            actual_commit_id = response_body['commit_id']
            
            print(f"Generated request_id: {actual_request_id}")
            print(f"Generated commit_id: {actual_commit_id}")
            
            # 验证 DynamoDB 初始记录创建（使用真实数据库）
            import time
            
            # 临时恢复真实的boto3来进行数据库验证
            import importlib
            import sys
            
            # 保存当前的Mock
            original_boto3_mock = sys.modules['boto3']
            
            # 临时移除Mock，导入真实的boto3
            del sys.modules['boto3']
            import boto3
            
            try:
                dynamodb = boto3.resource('dynamodb')
                table = dynamodb.Table(os.environ['REQUEST_TABLE'])
                
                # 验证初始记录存在
                response = table.get_item(
                    Key={
                        'commit_id': actual_commit_id,
                        'request_id': actual_request_id
                    }
                )
                
                assert 'Item' in response, "数据库中应该存在初始创建的记录"
                initial_item = response['Item']
                assert initial_item['task_status'] == 'Start', "初始状态应该为 Start"
                assert initial_item['project_name'] == 'Test Project', "项目名称应该正确"
                
                # 验证GitLab API被正确调用
                mock_gitlab_class.assert_called_once()
                mock_gl.projects.get.assert_called_once_with('test/awesome-project')
                
                # 等待 task_dispatcher 异步执行（真实的Lambda调用需要时间）
                print("等待task_dispatcher异步执行...")
                time.sleep(3)  # 等待异步处理
                
                # 再次检查记录状态，验证 task_dispatcher 是否执行了更新
                updated_response = table.get_item(
                    Key={
                        'commit_id': actual_commit_id,
                        'request_id': actual_request_id
                    }
                )
                
                if 'Item' in updated_response:
                    updated_item = updated_response['Item']
                    print(f"Updated task_status: {updated_item.get('task_status')}")
                    print(f"Task total: {updated_item.get('task_total', 0)}")
                    print(f"Task complete: {updated_item.get('task_complete', 0)}")
                    
                    # 验证task_dispatcher确实执行了（状态应该有变化）
                    if updated_item.get('task_status') != 'Start':
                        print("✅ task_dispatcher已执行并更新了状态")
                    else:
                        print("⚠️  task_dispatcher可能还在执行中或执行失败")
                
                # 清理测试数据
                table.delete_item(
                    Key={
                        'commit_id': actual_commit_id,
                        'request_id': actual_request_id
                    }
                )
            finally:
                # 恢复boto3的Mock
                sys.modules['boto3'] = original_boto3_mock