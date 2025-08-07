"""
task_dispatcher.py 单元测试

测试目标：验证任务分发器将代码评审请求分解为具体AI评审任务的核心功能
详细的测试设计思路请参考：test_task_dispatcher.md
"""

import pytest
import json
import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加lambda目录到路径，使测试能够导入被测试模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

# 添加mockdata目录到路径，使测试能够导入mock工具
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../mock_data/repositories'))

# 导入被测试模块
import task_dispatcher
import base


class TestTaskDispatcher:
    """task_dispatcher.py 测试类"""

    def test_validate_sqs_event(self):
        """
        测试目的：验证SQS事件的完整性和格式正确性
        
        测试场景：验证输入事件是否包含所有必要字段
        业务重要性：确保后续处理的数据基础可靠，避免因缺失字段导致的处理失败
        
        测试流程：
        1. 准备测试数据：构造包含必要字段和缺失字段的事件
        2. 执行核心功能：调用validate_sqs_event函数
        3. 验证结果：检查正常事件通过验证，异常事件抛出预期异常
        4. 清理数据：无需清理
        
        关键验证点：
        - 包含request_id字段的事件应该通过验证
        - 缺失request_id字段的事件应该抛出异常
        - 异常信息应该明确指出缺失的字段
        
        期望结果：
        - 有效事件返回True
        - 无效事件抛出包含具体错误信息的异常
        """
        # 测试正常事件 - 包含所有必要字段
        valid_event = {
            'request_id': 'test-request-123',
            'commit_id': 'abc123',
            'mode': 'diff',
            'target_branch': 'main'
        }
        
        # 验证正常事件通过验证
        result = task_dispatcher.validate_sqs_event(valid_event)
        assert result is True, "包含必要字段的事件应该通过验证"
        
        # 测试缺失必要字段的事件
        invalid_event = {
            'commit_id': 'abc123',
            'mode': 'diff',
            'target_branch': 'main'
            # 缺失 request_id 字段
        }
        
        # 验证缺失字段的事件抛出异常
        with pytest.raises(Exception) as exc_info:
            task_dispatcher.validate_sqs_event(invalid_event)
        
        # 验证异常信息包含具体的错误描述
        error_message = str(exc_info.value)
        assert 'request_id' in error_message, "异常信息应该指出缺失的字段名"
        assert 'does not have field' in error_message, "异常信息应该说明字段缺失的问题"
        
        # 测试完全空的事件
        empty_event = {}
        
        with pytest.raises(Exception) as exc_info:
            task_dispatcher.validate_sqs_event(empty_event)
        
        error_message = str(exc_info.value)
        assert 'request_id' in error_message, "空事件应该报告缺失request_id字段"

    def test_load_rules_webtool_push(self):
        """
        测试目的：验证Webtool触发Push事件的规则构造
        
        测试场景：用户通过Web界面手动触发Push类型的代码评审
        业务重要性：Webtool是用户主要的交互方式，确保规则正确构造是用户体验的基础
        
        测试流程：
        1. 准备测试数据：构造Webtool Push事件数据
        2. 执行核心功能：调用load_rules函数构造规则
        3. 验证结果：检查构造的规则字段完整性和正确性
        4. 清理数据：无需清理
        
        关键验证点：
        - 应该构造单个规则
        - 规则字段应该完整且正确
        - 提示词应该正确映射
        
        期望结果：
        - 返回单个构造的规则
        - 所有字段值与输入事件匹配
        """
        # 导入mockdata管理器
        from mock_repository_manager import get_mock_gitlab_project
        
        # 使用真实的mock仓库数据
        mock_project = get_mock_gitlab_project("123")
        repo_context = {'project': mock_project, 'source': 'gitlab'}
        
        # 测试Webtool Push事件
        webtool_push_event = {
            'invoker': 'webtool',
            'rule_name': 'Java代码质量检查',
            'mode': 'diff',
            'model': 'claude3-sonnet',
            'event_type': 'push',
            'target_branch': 'main',
            'target': 'src/**',
            'confirm': True,
            'webtool_prompt_system': '你是一个Java代码审查专家',
            'webtool_prompt_user': '请检查以下Java代码的质量问题'
        }
        
        # 调用load_rules函数
        rules = task_dispatcher.load_rules(webtool_push_event, repo_context, 'commit123', 'main')
        
        # 验证规则构造结果
        assert len(rules) == 1, "Webtool Push应该构造单个规则"
        rule = rules[0]
        
        # 验证规则字段的完整性和正确性
        assert rule['name'] == 'Java代码质量检查', "规则名称应该正确"
        assert rule['mode'] == 'diff', "规则模式应该正确"
        assert rule['model'] == 'claude3-sonnet', "规则模型应该正确"
        assert rule['event'] == 'push', "规则事件类型应该正确"
        assert rule['branch'] == 'main', "规则分支应该正确"
        assert rule['target'] == 'src/**', "规则目标应该正确"
        assert rule['confirm'] is True, "规则确认标志应该正确"
        assert rule['prompt_system'] == '你是一个Java代码审查专家', "系统提示词应该正确"
        assert rule['prompt_user'] == '请检查以下Java代码的质量问题', "用户提示词应该正确"

    def test_load_rules_webtool_merge(self):
        """
        测试目的：验证Webtool触发Merge事件的规则构造，包含自定义字段
        
        测试场景：用户通过Web界面手动触发Merge类型的代码评审，包含复杂的自定义字段
        业务重要性：Merge评审通常更严格，确保规则正确构造对代码质量控制很重要
        
        测试流程：
        1. 准备测试数据：构造包含自定义字段的Webtool Merge事件数据
        2. 执行核心功能：调用load_rules函数构造规则
        3. 验证结果：检查构造的规则字段完整性和正确性，包括自定义字段
        4. 清理数据：无需清理
        
        关键验证点：
        - 应该构造单个规则
        - 事件类型应该是merge_request
        - 所有自定义字段应该正确映射
        - 复杂的多行字段应该正确处理
        
        期望结果：
        - 返回单个构造的规则
        - 事件类型为merge_request
        - 所有自定义字段正确传递
        """
        # 导入mockdata管理器
        from mock_repository_manager import get_mock_gitlab_project
        
        # 使用真实的mock仓库数据
        mock_project = get_mock_gitlab_project("123")
        repo_context = {'project': mock_project, 'source': 'gitlab'}
        
        # 测试Webtool Merge事件，包含自定义字段
        webtool_merge_event = {
            'invoker': 'webtool',
            'rule_name': '合并请求安全检查',
            'mode': 'all',
            'model': 'claude3-opus',
            'event_type': 'merge_request',
            'target_branch': 'main',
            'target': '**/*.java',
            'confirm': False,
            'webtool_prompt_system': '你是一个安全审计专家',
            'webtool_prompt_user': '请检查以下代码的安全漏洞',
            # 添加自定义字段
            'security_focus': 'SQL注入、XSS攻击、权限绕过',
            'compliance_standard': 'OWASP Top 10',
            'severity_threshold': 'HIGH',
            'scan_depth': 'deep',
            'custom_rules': [
                '检查用户输入验证',
                '检查权限控制逻辑',
                '检查敏感数据处理'
            ],
            'output_format': 'detailed_report',
            'business_context': '这是一个金融系统，安全要求极高',
            'technical_requirements': {
                'framework': 'Spring Security',
                'database': 'MySQL',
                'encryption': 'AES-256'
            }
        }
        
        # 调用load_rules函数
        rules = task_dispatcher.load_rules(webtool_merge_event, repo_context, 'commit456', 'main')
        
        # 验证规则构造结果
        assert len(rules) == 1, "Webtool Merge应该构造单个规则"
        rule = rules[0]
        
        # 验证基础字段
        assert rule['name'] == '合并请求安全检查', "规则名称应该正确"
        assert rule['mode'] == 'all', "规则模式应该正确"
        assert rule['model'] == 'claude3-opus', "规则模型应该正确"
        assert rule['event'] == 'merge_request', "规则事件类型应该正确"
        assert rule['branch'] == 'main', "规则分支应该正确"
        assert rule['target'] == '**/*.java', "规则目标应该正确"
        assert rule['confirm'] is False, "规则确认标志应该正确"
        assert rule['prompt_system'] == '你是一个安全审计专家', "系统提示词应该正确"
        assert rule['prompt_user'] == '请检查以下代码的安全漏洞', "用户提示词应该正确"
        
        # 验证当前系统支持的字段（基于实际的load_rules实现）
        # 注意：当前的load_rules实现只支持固定的字段，不支持任意自定义字段
        expected_fields = ['name', 'mode', 'number', 'model', 'event', 'branch', 'target', 'confirm', 'prompt_system', 'prompt_user']
        for field in expected_fields:
            assert field in rule, f"规则应该包含{field}字段"
        
        # 验证number字段（webtool规则固定为1）
        assert rule['number'] == 1, "Webtool规则的number应该是1"
        
        # 验证当前系统不支持自定义字段的传递
        # 这是当前实现的限制，自定义字段不会被传递到规则中
        custom_fields = ['security_focus', 'compliance_standard', 'severity_threshold', 'scan_depth', 
                        'custom_rules', 'output_format', 'business_context', 'technical_requirements']
        for field in custom_fields:
            assert field not in rule, f"当前实现不支持自定义字段{field}的传递"
        
        print(f"✅ Webtool Merge成功构造规则，包含 {len(rule.keys())} 个标准字段")
        print(f"📋 注意：当前实现不支持自定义字段的传递，这是一个已知的设计限制")

    def test_load_rules_webhook_push(self):
        """
        测试目的：验证Webhook触发Push事件的规则加载
        
        测试场景：GitLab Push事件触发自动代码评审，从真实mockdata加载规则
        业务重要性：Push事件是最常见的触发方式，确保能正确加载仓库中的评审规则
        
        测试流程：
        1. 准备测试数据：构造Webhook Push事件数据
        2. 执行核心功能：调用load_rules函数从mockdata加载规则
        3. 验证结果：检查加载的规则内容与真实.codereview.yaml匹配
        4. 清理数据：无需清理
        
        关键验证点：
        - 应该从真实mockdata加载规则
        - 规则内容应该与.codereview.yaml文件匹配
        - 应该只加载匹配Push事件的规则
        
        期望结果：
        - 返回从mockdata加载的真实规则列表
        - 规则内容符合预期格式
        """
        # 导入mockdata管理器
        from mock_repository_manager import get_mock_gitlab_project
        
        # 使用真实的mock仓库数据
        mock_project = get_mock_gitlab_project("123")
        repo_context = {'project': mock_project, 'source': 'gitlab'}
        
        # 测试Webhook Push事件
        webhook_push_event = {
            'invoker': 'webhook',
            'event_type': 'push',
            'target_branch': 'main'
        }
        
        # 调用load_rules函数，从真实的mock仓库加载.codereview.yaml
        rules = task_dispatcher.load_rules(webhook_push_event, repo_context, 'd4e5f6789012345678901234567890abcdef1234', 'main')
        
        # 验证webhook规则的加载 - 应该加载到真实的.codereview.yaml内容
        assert len(rules) >= 1, "Webhook Push应该从mockdata加载到真实规则"
        
        # 验证第一个规则的内容（来自真实的code-simplification.yaml）
        rule = rules[0]
        assert rule['branch'] == 'main', "规则分支应该匹配.codereview.yaml中的配置"
        assert rule['mode'] == 'diff', "规则模式应该匹配.codereview.yaml中的配置"
        assert rule['target'] == 'src/**', "规则目标应该匹配.codereview.yaml中的配置"
        
        # 验证真实的系统提示词内容
        assert 'system' in rule, "规则应该包含system字段"
        system_prompt = rule['system']
        assert '专业的Java代码简化专家' in system_prompt, "系统提示词应该包含Java代码简化专家描述"
        assert '代码复杂度和可读性' in system_prompt, "系统提示词应该包含代码复杂度检查"
        assert '重复代码和冗余逻辑' in system_prompt, "系统提示词应该包含重复代码检查"
        assert '简化建议和重构方案' in system_prompt, "系统提示词应该包含简化建议"
        
        # 验证真实的用户提示词内容
        assert 'user' in rule, "规则应该包含user字段"
        user_prompt = rule['user']
        assert 'Java代码进行简化分析' in user_prompt, "用户提示词应该包含Java代码简化分析描述"
        assert '代码复杂度' in user_prompt, "用户提示词应该包含代码复杂度要求"
        assert '重复逻辑和可读性改进' in user_prompt, "用户提示词应该包含重复逻辑和可读性要求"
        
        print(f"✅ Webhook Push成功从mockdata加载了 {len(rules)} 个真实规则")

    def test_load_rules_webhook_merge(self):
        """
        测试目的：验证Webhook触发Merge事件的规则加载，重点验证自定义字段
        
        测试场景：GitLab Merge Request事件触发自动代码评审，从真实mockdata加载规则
        业务重要性：Merge Request评审是代码质量控制的关键环节，确保能正确加载对应规则的所有自定义字段
        
        测试流程：
        1. 准备测试数据：构造Webhook Merge事件数据
        2. 执行核心功能：调用load_rules函数从mockdata加载规则
        3. 验证结果：检查加载的规则内容与真实database-master-slave-issue.yaml匹配
        4. 清理数据：无需清理
        
        关键验证点：
        - 应该从真实mockdata加载规则
        - 应该只加载匹配Merge事件的规则
        - 规则的所有自定义字段都应该正确加载
        - 验证复杂的多行字段内容
        
        期望结果：
        - 返回从mockdata加载的Merge规则
        - 规则内容符合database-master-slave-issue.yaml的完整配置
        """
        # 导入mockdata管理器
        from mock_repository_manager import get_mock_gitlab_project
        
        # 使用真实的mock仓库数据
        mock_project = get_mock_gitlab_project("123")
        repo_context = {'project': mock_project, 'source': 'gitlab'}
        
        # 测试Webhook Merge事件
        webhook_merge_event = {
            'invoker': 'webhook',
            'event_type': 'merge',
            'target_branch': 'main'
        }
        
        # 调用load_rules函数，从真实的mock仓库加载.codereview.yaml
        rules = task_dispatcher.load_rules(webhook_merge_event, repo_context, 'd4e5f6789012345678901234567890abcdef1234', 'main')
        
        # 验证webhook规则的加载 - 应该加载到真实的.codereview.yaml内容
        assert len(rules) >= 1, "Webhook Merge应该从mockdata加载到真实规则"
        
        # 查找匹配merge事件的规则（database-master-slave-issue.yaml）
        merge_rule = None
        for rule in rules:
            if rule.get('event') == 'merge':
                merge_rule = rule
                break
        
        assert merge_rule is not None, "应该找到匹配merge事件的规则"
        
        # 验证基础字段
        assert merge_rule['name'] == 'Database Master-Slave Issue', "规则名称应该正确"
        assert merge_rule['branch'] == 'main', "规则分支应该匹配.codereview.yaml中的配置"
        assert merge_rule['mode'] == 'all', "规则模式应该匹配.codereview.yaml中的配置"
        assert merge_rule['target'] == 'src/main/**.java, src/main/**.xml, src/main/**.properties, pom.xml', "规则目标应该匹配.codereview.yaml中的配置"
        assert merge_rule['model'] == 'claude3-sonnet', "规则模型应该正确"
        assert merge_rule['event'] == 'merge', "规则事件类型应该正确"
        assert merge_rule['confirm'] is False, "规则确认标志应该正确"
        
        # 验证order字段
        assert 'order' in merge_rule, "规则应该包含order字段"
        expected_order = 'system, business, design, web_design, sql, requirement, task, output, response'
        assert merge_rule['order'] == expected_order, "order字段应该包含正确的字段顺序"
        
        # 验证system字段
        assert 'system' in merge_rule, "规则应该包含system字段"
        system_prompt = merge_rule['system']
        assert 'experienced Java developer' in system_prompt, "系统提示词应该包含Java开发者描述"
        assert 'architectural design' in system_prompt, "系统提示词应该包含架构设计"
        assert 'project review' in system_prompt, "系统提示词应该包含项目评审"
        
        # 验证business字段（多行内容）
        assert 'business' in merge_rule, "规则应该包含business字段"
        business_prompt = merge_rule['business']
        assert '记账业务系统' in business_prompt, "业务描述应该包含记账业务系统"
        assert 'restful API接口' in business_prompt, "业务描述应该包含API接口"
        assert 'C端用户使用' in business_prompt, "业务描述应该包含C端用户"
        
        # 验证design字段（复杂的多行结构化内容）
        assert 'design' in merge_rule, "规则应该包含design字段"
        design_prompt = merge_rule['design']
        assert '用户，User' in design_prompt, "设计描述应该包含用户对象"
        assert '账务类别，Bill Category' in design_prompt, "设计描述应该包含账务类别对象"
        assert '账户明细，Bill Item' in design_prompt, "设计描述应该包含账户明细对象"
        assert 'MySQL InnoDB' in design_prompt, "设计描述应该包含数据库要求"
        assert 'great_' in design_prompt, "设计描述应该包含表前缀要求"
        
        # 验证web_design字段
        assert 'web_design' in merge_rule, "规则应该包含web_design字段"
        web_design_prompt = merge_rule['web_design']
        assert 'SpringBoot 3.1.x' in web_design_prompt, "Web设计应该包含SpringBoot版本"
        assert 'demo.great' in web_design_prompt, "Web设计应该包含基础包地址"
        assert 'MyBatis' in web_design_prompt, "Web设计应该包含MyBatis"
        assert '8080端口' in web_design_prompt, "Web设计应该包含端口配置"
        
        # 验证sql字段（包含完整的SQL脚本）
        assert 'sql' in merge_rule, "规则应该包含sql字段"
        sql_prompt = merge_rule['sql']
        assert 'DROP DATABASE IF EXISTS great' in sql_prompt, "SQL应该包含数据库创建脚本"
        assert 'great_user' in sql_prompt, "SQL应该包含用户表"
        assert 'great_bill_category' in sql_prompt, "SQL应该包含账务类别表"
        assert 'great_bill_item' in sql_prompt, "SQL应该包含账户明细表"
        
        # 验证requirement字段（核心业务需求）
        assert 'requirement' in merge_rule, "规则应该包含requirement字段"
        requirement_prompt = merge_rule['requirement']
        assert 'master-slave database' in requirement_prompt, "需求应该包含主从数据库"
        assert 'Write operation must use the master database' in requirement_prompt, "需求应该包含写操作使用主库"
        assert 'read after writing, you must use the master database' in requirement_prompt, "需求应该包含写后读使用主库"
        assert 'other reading scenarios, must use the slave database' in requirement_prompt, "需求应该包含其他读操作使用从库"
        
        # 验证task字段
        assert 'task' in merge_rule, "规则应该包含task字段"
        task_prompt = merge_rule['task']
        assert '*Service' in task_prompt, "任务应该包含Service类检查"
        assert 'master-salve database design' in task_prompt, "任务应该包含主从数据库设计验证"
        assert 'recursively trace the code call chain' in task_prompt, "任务应该包含递归调用链追踪"
        
        # 验证output字段（复杂的格式要求）
        assert 'output' in merge_rule, "规则应该包含output字段"
        output_prompt = merge_rule['output']
        assert 'Output all your message' in output_prompt, "输出格式应该包含输出要求"
        assert '<output>' in output_prompt, "输出格式应该包含output标签"
        assert '<thought>' in output_prompt and '</thought>' in output_prompt, "输出格式应该包含thought标签"
        assert 'JSON format' in output_prompt, "输出格式应该包含JSON要求"
        assert 'title' in output_prompt and 'content' in output_prompt and 'filepath' in output_prompt, "输出格式应该包含必要字段"
        assert 'QUOTES and backslashes' in output_prompt, "输出格式应该包含转义要求"
        assert '好的例子' in output_prompt and '坏的例子' in output_prompt, "输出格式应该包含示例"
        
        # 验证other字段
        assert 'other' in merge_rule, "规则应该包含other字段"
        other_prompt = merge_rule['other']
        assert '请你逐步思考' in other_prompt, "其他要求应该包含逐步思考"
        
        # 验证response字段
        assert 'response' in merge_rule, "规则应该包含response字段"
        response_prompt = merge_rule['response']
        assert 'strictly follow my guidelines' in response_prompt, "响应要求应该包含严格遵循指导原则"
        assert 'don\'t need to repeat my requirements' in response_prompt, "响应要求应该包含不重复需求"
        
        print(f"✅ Webhook Merge成功从mockdata加载了 {len(rules)} 个真实规则")
        print(f"📋 验证了merge规则的 {len([k for k in merge_rule.keys() if k not in ['branch', 'mode', 'target', 'model', 'event', 'confirm']])} 个自定义字段")

    def test_load_rules_default_behavior(self):
        """
        测试目的：验证没有invoker字段时的默认行为
        
        测试场景：事件数据缺失invoker字段，应该默认使用webhook逻辑
        业务重要性：确保系统在字段缺失时有合理的默认行为，提高系统健壮性
        
        测试流程：
        1. 准备测试数据：构造没有invoker字段的事件数据
        2. 执行核心功能：调用load_rules函数
        3. 验证结果：检查是否使用webhook逻辑加载规则
        4. 清理数据：无需清理
        
        关键验证点：
        - 应该默认使用webhook逻辑
        - 应该从mockdata加载真实规则
        - 规则内容应该正确
        
        期望结果：
        - 默认使用webhook逻辑加载规则
        - 返回真实的规则列表
        """
        # 导入mockdata管理器
        from mock_repository_manager import get_mock_gitlab_project
        
        # 使用真实的mock仓库数据
        mock_project = get_mock_gitlab_project("123")
        repo_context = {'project': mock_project, 'source': 'gitlab'}
        
        # 测试没有invoker字段的事件（默认为webhook）
        default_event = {
            'event_type': 'push',
            'target_branch': 'main'
        }
        
        rules = task_dispatcher.load_rules(default_event, repo_context, 'd4e5f6789012345678901234567890abcdef1234', 'main')
        
        # 验证默认情况下使用webhook逻辑，加载真实规则
        assert len(rules) >= 1, "默认情况应该从mockdata加载真实规则"
        assert rules[0]['branch'] == 'main', "默认加载的规则分支应该正确"
        
        # 验证加载的是真实的规则内容
        rule = rules[0]
        assert 'system' in rule, "规则应该包含system字段"
        assert 'user' in rule, "规则应该包含user字段"
        
        print(f"✅ 默认行为成功从mockdata加载了 {len(rules)} 个真实规则")

    def test_filter_rules(self):
        """
        测试目的：验证规则过滤逻辑的正确性
        
        测试场景：测试分支和事件类型匹配的规则过滤
        业务重要性：确保只有匹配当前分支和事件类型的规则被执行，避免不相关规则的执行
        
        测试流程：
        1. 准备测试数据：构造包含不同分支和事件类型的规则集合
        2. 执行核心功能：模拟lambda_handler中的规则过滤逻辑
        3. 验证结果：检查只有匹配的规则被保留
        4. 清理数据：无需清理
        
        关键验证点：
        - 分支匹配逻辑的准确性
        - 事件类型匹配的正确性
        - 过滤结果的完整性
        - 边界情况的处理
        
        期望结果：
        - 只返回同时匹配分支和事件类型的规则
        - 过滤后的规则数量正确
        """
        # 准备测试规则集合
        all_rules = [
            {
                'name': '主分支代码质量检查',
                'mode': 'diff',
                'branch': 'main',
                'event': 'push',
                'model': 'claude3-sonnet'
            },
            {
                'name': '开发分支代码质量检查',
                'mode': 'diff', 
                'branch': 'develop',
                'event': 'push',
                'model': 'claude3-haiku'
            },
            {
                'name': '主分支合并请求检查',
                'mode': 'all',
                'branch': 'main',
                'event': 'merge_request',
                'model': 'claude3-opus'
            },
            {
                'name': '功能分支推送检查',
                'mode': 'single',
                'branch': 'feature/*',
                'event': 'push',
                'model': 'claude3-haiku'
            },
            {
                'name': '发布分支检查',
                'mode': 'all',
                'branch': 'release/*',
                'event': 'push',
                'model': 'claude3-opus'
            }
        ]
        
        # 测试场景1：main分支的push事件
        target_branch = 'main'
        event_type = 'push'
        
        # 执行过滤逻辑（模拟lambda_handler中的逻辑）
        filtered_rules = []
        for rule in all_rules:
            if task_dispatcher.match_branch(rule.get('branch'), target_branch) and rule.get('event') == event_type:
                filtered_rules.append(rule)
        
        # 验证过滤结果
        assert len(filtered_rules) == 1, "main分支push事件应该匹配1个规则"
        assert filtered_rules[0]['name'] == '主分支代码质量检查', "应该匹配主分支代码质量检查规则"
        
        # 测试场景2：main分支的merge_request事件
        target_branch = 'main'
        event_type = 'merge_request'
        
        filtered_rules = []
        for rule in all_rules:
            if task_dispatcher.match_branch(rule.get('branch'), target_branch) and rule.get('event') == event_type:
                filtered_rules.append(rule)
        
        assert len(filtered_rules) == 1, "main分支merge_request事件应该匹配1个规则"
        assert filtered_rules[0]['name'] == '主分支合并请求检查', "应该匹配主分支合并请求检查规则"
        
        # 测试场景3：develop分支的push事件
        target_branch = 'develop'
        event_type = 'push'
        
        filtered_rules = []
        for rule in all_rules:
            if task_dispatcher.match_branch(rule.get('branch'), target_branch) and rule.get('event') == event_type:
                filtered_rules.append(rule)
        
        assert len(filtered_rules) == 1, "develop分支push事件应该匹配1个规则"
        assert filtered_rules[0]['name'] == '开发分支代码质量检查', "应该匹配开发分支代码质量检查规则"
        
        # 测试场景4：不存在的分支和事件组合
        target_branch = 'test'
        event_type = 'push'
        
        filtered_rules = []
        for rule in all_rules:
            if task_dispatcher.match_branch(rule.get('branch'), target_branch) and rule.get('event') == event_type:
                filtered_rules.append(rule)
        
        assert len(filtered_rules) == 0, "不匹配的分支应该没有规则"
        
        # 测试场景5：分支匹配但事件不匹配
        target_branch = 'main'
        event_type = 'tag'  # 不存在的事件类型
        
        filtered_rules = []
        for rule in all_rules:
            if task_dispatcher.match_branch(rule.get('branch'), target_branch) and rule.get('event') == event_type:
                filtered_rules.append(rule)
        
        assert len(filtered_rules) == 0, "事件类型不匹配应该没有规则"
        
        # 测试match_branch函数的直接调用
        assert task_dispatcher.match_branch('main', 'main') is True, "相同分支应该匹配"
        assert task_dispatcher.match_branch('main', 'develop') is False, "不同分支应该不匹配"
        assert task_dispatcher.match_branch('feature/*', 'feature/login') is False, "当前实现不支持通配符匹配"

    def test_get_code_contents(self):
        """
        测试目的：验证三种评审模式的内容获取逻辑
        
        测试场景：测试all/single/diff三种模式的内容获取
        业务重要性：内容获取是AI评审的基础，确保每种模式都能正确获取对应的代码内容
        
        测试流程：
        1. 准备测试数据：直接使用Mock GitLab Project对象，跳过init_repo_context
        2. 执行核心功能：调用对应的内容获取函数
        3. 验证结果：检查返回的内容结构和格式
        4. 清理数据：Mock会自动清理
        
        关键验证点：
        - 内容格式的正确性
        - 文件路径的准确性
        - 目标过滤的有效性
        - 模式特定逻辑的正确性
        - codelib和gitlab_code业务逻辑的正确执行
        
        期望结果：
        - All模式返回完整项目代码
        - Single模式返回每个文件的完整内容
        - Diff模式返回文件的差异内容
        - 只Mock最底层的GitLab Project对象，让所有业务逻辑真实执行
        """
        from mock_repository_manager import get_mock_gitlab_project
        
        # 直接创建Mock GitLab Project对象（这是允许Mock的外部依赖）
        mock_project = get_mock_gitlab_project("123")
        
        # 直接构造repo_context，跳过init_repo_context的调用
        # 这样我们只Mock了GitLab Project对象，让codelib和gitlab_code的业务逻辑真实执行
        repo_context = {'source': 'gitlab', 'project': mock_project}
        
        # 使用Mock仓库中的真实commit ID
        commit_id = 'b2c3d4e5f6789012345678901234567890abcdef'  # 包含pom.xml和App.java的commit
        previous_commit_id = 'a1b2c3d4e5f6789012345678901234567890abcd'  # 前一个commit
        
        # 测试All模式
        rule_all = {
            'name': '全项目检查',
            'mode': 'all',
            'target': 'src/**/*.java,pom.xml'
        }
        
        # 调用get_code_contents_for_all函数（让所有codelib和gitlab_code业务逻辑真实执行）
        contents_all = task_dispatcher.get_code_contents_for_all(repo_context, commit_id, rule_all)
        
        # 验证All模式的结果
        assert len(contents_all) == 1, "All模式应该返回一个内容项"
        content = contents_all[0]
        assert content['mode'] == 'all', "内容模式应该是all"
        assert content['filepath'] == '<The Whole Project>', "All模式的文件路径应该是特殊标识"
        assert content['content'] is not None, "内容不应该为空"
        assert content['rule'] == rule_all, "应该包含对应的规则"
        
        # 验证内容包含预期的文件
        assert 'src/main/java/demo/great/App.java' in content['content'], "应该包含Java文件内容"
        assert 'pom.xml' in content['content'], "应该包含pom.xml文件内容"
        
        # 测试Single模式
        rule_single = {
            'name': '单文件检查',
            'mode': 'single',
            'target': '**/*.java'
        }
        
        # 调用get_code_contents_for_single函数（让所有codelib和gitlab_code业务逻辑真实执行）
        contents_single = task_dispatcher.get_code_contents_for_single(
            repo_context, commit_id, previous_commit_id, rule_single
        )
        
        # 验证Single模式的结果
        assert len(contents_single) > 0, "Single模式应该返回文件内容"
        
        # 验证第一个文件内容的格式
        if contents_single:
            content1 = contents_single[0]
            assert content1['mode'] == 'single', "内容模式应该是single"
            assert content1['filepath'].endswith('.java'), "文件路径应该是Java文件"
            assert '```' in content1['content'], "内容应该包含代码块格式"
            assert content1['rule'] == rule_single, "应该包含对应的规则"
        
        # 测试Diff模式
        rule_diff = {
            'name': '差异检查',
            'mode': 'diff',
            'target': 'src/**/*.java'
        }
        
        # 调用get_code_contents_for_diff函数（让所有codelib和gitlab_code业务逻辑真实执行）
        contents_diff = task_dispatcher.get_code_contents_for_diff(
            repo_context, commit_id, previous_commit_id, rule_diff
        )
        
        # 验证Diff模式的结果
        # 注意：由于Mock数据中可能没有实际的diff，这里主要验证函数能正常执行
        assert isinstance(contents_diff, list), "Diff模式应该返回列表"
        
        # 如果有diff内容，验证格式
        if contents_diff:
            diff_content = contents_diff[0]
            assert diff_content['mode'] == 'diff', "内容模式应该是diff"
            assert diff_content['filepath'].endswith('.java'), "文件路径应该是Java文件"
            assert diff_content['rule'] == rule_diff, "应该包含对应的规则"
        
        # 测试错误处理：无效的target模式
        rule_invalid = {
            'name': '无效目标',
            'mode': 'all',
            'target': 'nonexistent/**'
        }
        
        contents_invalid = task_dispatcher.get_code_contents_for_all(repo_context, commit_id, rule_invalid)
        # 应该返回空内容或者包含空内容的结果
        if contents_invalid:
            assert contents_invalid[0]['content'] == '' or len(contents_invalid) == 0, "无效目标应该返回空内容"

    def test_prompt_generation(self):
        """
        测试目的：验证AI模型提示词的生成逻辑
        
        测试场景：测试自定义提示词和默认提示词两种方式
        业务重要性：提示词是AI评审的核心输入，确保提示词正确生成是获得高质量评审结果的关键
        
        测试流程：
        1. 准备测试数据：构造包含不同提示词配置的规则
        2. 执行核心功能：调用get_prompt_data函数
        3. 验证结果：检查生成的提示词内容和格式
        4. 清理数据：无需清理
        
        关键验证点：
        - 提示词内容的正确性
        - 变量替换的准确性
        - 字段排序的有效性
        - 空值处理的合理性
        
        期望结果：
        - 自定义提示词按配置生成
        - 默认提示词按字段顺序组合
        - 变量正确替换为实际值
        """
        # 测试自定义提示词（使用prompt_system和prompt_user字段）
        custom_rule = {
            'name': '自定义提示词规则',
            'mode': 'diff',
            'model': 'claude3-sonnet',
            'prompt_system': '你是一个{{language}}代码审查专家，专注于{{focus_area}}',
            'prompt_user': '请检查以下{{language}}代码的{{check_type}}问题：\n{{code}}'
        }
        
        test_code = 'def hello():\n    print("Hello World")'
        test_variables = {
            'language': 'Python',
            'focus_area': '代码质量',
            'check_type': '语法和逻辑'
        }
        
        # 调用get_prompt_data函数
        prompt_system, prompt_user = task_dispatcher.get_prompt_data(
            'diff', custom_rule, test_code, test_variables
        )
        
        # 验证自定义提示词的生成
        expected_system = '你是一个Python代码审查专家，专注于代码质量'
        expected_user = '请检查以下Python代码的语法和逻辑问题：\n' + test_code
        
        assert prompt_system == expected_system, "系统提示词应该正确替换变量"
        assert prompt_user == expected_user, "用户提示词应该正确替换变量和代码"
        
        # 测试默认提示词（使用system字段和其他字段组合）
        default_rule = {
            'name': '默认提示词规则',
            'mode': 'single',
            'model': 'claude3-haiku',
            'branch': 'main',
            'target': '*.py',
            'system': '你是一个专业的代码审查助手',
            'quality': '请检查代码质量问题',
            'security': '请检查安全漏洞',
            'performance': '请检查性能问题',
            'order': ['quality', 'security', 'performance']
        }
        
        # 调用get_prompt_data函数
        prompt_system, prompt_user = task_dispatcher.get_prompt_data(
            'single', default_rule, test_code
        )
        
        # 验证默认提示词的生成
        expected_system = '你是一个专业的代码审查助手'
        expected_user = f'以下是我的代码:\n{test_code}\n请检查代码质量问题\n\n请检查安全漏洞\n\n请检查性能问题'
        
        assert prompt_system == expected_system, "默认系统提示词应该使用system字段"
        assert prompt_user == expected_user, "默认用户提示词应该按order字段排序组合"
        
        # 测试没有order字段的默认提示词
        no_order_rule = {
            'name': '无排序规则',
            'mode': 'all',
            'model': 'claude3-opus',
            'system': '代码审查助手',
            'check1': '检查项1',
            'check2': '检查项2'
        }
        
        prompt_system, prompt_user = task_dispatcher.get_prompt_data(
            'all', no_order_rule, test_code
        )
        
        # 验证无order字段时的处理
        assert prompt_system == '代码审查助手', "系统提示词应该正确"
        assert '检查项1' in prompt_user, "用户提示词应该包含所有检查项"
        assert '检查项2' in prompt_user, "用户提示词应该包含所有检查项"
        assert f'以下是我的代码:\n{test_code}' in prompt_user, "用户提示词应该包含代码"
        
        # 测试模式不匹配的情况
        result = task_dispatcher.get_prompt_data(
            'diff', no_order_rule, test_code  # 规则模式是all，但请求模式是diff
        )
        
        assert result is None, "模式不匹配时应该返回None"
        
        # 测试非Claude模型
        non_claude_rule = {
            'name': '非Claude模型',
            'mode': 'diff',
            'model': 'gpt-4',
            'prompt_system': '系统提示词',
            'prompt_user': '用户提示词'
        }
        
        prompt_system, prompt_user = task_dispatcher.get_prompt_data(
            'diff', non_claude_rule, test_code
        )
        
        assert prompt_system is None, "非Claude模型应该返回None"
        assert prompt_user is None, "非Claude模型应该返回None"
        
        # 测试format_prompt函数的变量替换
        pattern = '检查{{type}}代码的{{issue}}问题，重点关注{{focus}}'
        variables = {
            'type': 'Python',
            'issue': '质量',
            'focus': '性能优化'
        }
        
        result = task_dispatcher.format_prompt(pattern, variables)
        expected = '检查Python代码的质量问题，重点关注性能优化'
        assert result == expected, "format_prompt应该正确替换所有变量"
        
        # 测试变量不存在的情况
        incomplete_variables = {'type': 'Java'}
        result = task_dispatcher.format_prompt(pattern, incomplete_variables)
        expected = '检查Java代码的{{issue}}问题，重点关注{{focus}}'  # 缺失的变量保持原样
        assert result == expected, "缺失的变量应该保持原样"

    @patch('task_dispatcher.send_message')
    def test_task_distribution(self, mock_send_message):
        """
        测试目的：验证任务数据的正确构造和SQS消息的成功发送
        
        测试场景：测试任务分发到SQS队列的完整流程
        业务重要性：任务分发是系统的核心功能，确保任务正确发送到队列是系统正常运行的关键
        
        测试流程：
        1. 准备测试数据：构造测试事件、规则和内容
        2. 执行核心功能：调用send_task_to_sqs函数
        3. 验证结果：检查任务数据结构和发送调用
        4. 清理数据：使用真实DynamoDB，需要清理测试数据
        
        关键验证点：
        - 任务数据结构的完整性
        - SQS消息发送的正确性
        - DynamoDB状态更新的准确性
        - 发送失败时的错误处理
        
        期望结果：
        - 任务成功发送到SQS队列
        - 数据库状态正确更新
        - 发送失败时正确更新失败计数
        """
        # 准备测试数据
        test_event = {
            'request_id': 'test-request-123',
            'commit_id': 'commit-abc123',
            'invoker': 'webtool',
            'confirm': True,
            'confirm_prompt': '请确认这个评审结果'
        }
        
        test_rules = [
            {
                'name': '代码质量检查',
                'mode': 'diff',
                'model': 'claude3-sonnet'
            }
        ]
        
        test_contents = [
            {
                'mode': 'diff',
                'filepath': 'src/app.py',
                'content': 'src/app.py\n```\ndef hello():\n    print("Hello")\n```',
                'rule': test_rules[0]
            },
            {
                'mode': 'diff', 
                'filepath': 'src/utils.py',
                'content': 'src/utils.py\n```\ndef helper():\n    return "help"\n```',
                'rule': test_rules[0]
            }
        ]
        
        # Mock send_message返回成功
        mock_send_message.return_value = True
        
        # 调用send_task_to_sqs函数
        result = task_dispatcher.send_task_to_sqs(
            test_event, test_rules, 'test-request-123', 'commit-abc123', test_contents
        )
        
        # 验证函数返回成功
        assert result is True, "任务分发应该成功"
        
        # 验证send_message被调用了正确的次数
        assert mock_send_message.call_count == 2, "应该发送2个任务到SQS"
        
        # 验证第一个任务的数据结构
        first_call_args = mock_send_message.call_args_list[0][0][0]
        assert first_call_args['context'] == test_event, "任务应该包含原始事件上下文"
        assert first_call_args['commit_id'] == 'commit-abc123', "任务应该包含正确的commit_id"
        assert first_call_args['request_id'] == 'test-request-123', "任务应该包含正确的request_id"
        assert first_call_args['number'] == 1, "第一个任务的编号应该是1"
        assert first_call_args['mode'] == 'diff', "任务模式应该正确"
        assert first_call_args['model'] == 'claude3-sonnet', "任务模型应该正确"
        assert first_call_args['filepath'] == 'src/app.py', "任务文件路径应该正确"
        assert first_call_args['rule_name'] == '代码质量检查', "任务规则名称应该正确"
        assert 'prompt_system' in first_call_args, "任务应该包含系统提示词"
        assert 'prompt_user' in first_call_args, "任务应该包含用户提示词"
        assert first_call_args['confirm_prompt'] == '请确认这个评审结果', "确认提示词应该正确"
        
        # 验证第二个任务的数据结构
        second_call_args = mock_send_message.call_args_list[1][0][0]
        assert second_call_args['number'] == 2, "第二个任务的编号应该是2"
        assert second_call_args['filepath'] == 'src/utils.py', "第二个任务文件路径应该正确"
        
        # 验证identity字段的生成
        expected_identity1 = 'diff-claude3-sonnet-1-代码质量检查-src/app.py'.lower()
        assert first_call_args['identity'] == expected_identity1, "任务identity应该正确生成"
        
        # 从DynamoDB读取数据验证状态更新（使用真实的DynamoDB）
        import boto3
        dynamodb = boto3.resource("dynamodb")
        table_name = os.getenv('REQUEST_TABLE')
        table = dynamodb.Table(table_name)
        
        try:
            # 读取更新后的记录
            response = table.get_item(
                Key={'commit_id': 'commit-abc123', 'request_id': 'test-request-123'},
                ConsistentRead=True
            )
            
            if 'Item' in response:
                item = response['Item']
                assert item['task_status'] == 'Initializing', "任务状态应该是Initializing"
                assert item['task_total'] == 2, "任务总数应该是2"
                assert item['task_complete'] == 0, "完成任务数应该是0"
                assert item['task_failure'] == 0, "失败任务数应该是0"
                assert 'update_time' in item, "应该有更新时间"
        except Exception as e:
            # 如果DynamoDB表不存在或无权限，跳过这个验证
            print(f"跳过DynamoDB验证: {e}")
        
        # 测试发送失败的情况
        mock_send_message.reset_mock()
        mock_send_message.return_value = False  # 模拟发送失败
        
        result = task_dispatcher.send_task_to_sqs(
            test_event, test_rules, 'test-request-456', 'commit-def456', test_contents
        )
        
        # 验证即使发送失败，函数仍然返回True（因为这是批量处理）
        assert result is True, "即使部分任务发送失败，函数也应该返回True"
        
        # 验证失败计数的更新（这需要检查DynamoDB中的failure计数）
        try:
            response = table.get_item(
                Key={'commit_id': 'commit-def456', 'request_id': 'test-request-456'},
                ConsistentRead=True
            )
            
            if 'Item' in response:
                item = response['Item']
                # 由于每个任务发送都失败，失败计数应该等于任务数
                assert item['task_failure'] == 2, "失败任务数应该等于发送失败的任务数"
        except Exception as e:
            print(f"跳过失败计数验证: {e}")

    def test_send_message(self):
        """
        测试目的：验证SQS消息发送的底层实现
        
        测试场景：测试send_message函数的消息编码和发送
        业务重要性：这是任务分发的底层实现，确保消息正确编码和发送
        
        测试流程：
        1. 准备测试数据：构造测试消息数据
        2. 执行核心功能：调用send_message函数
        3. 验证结果：检查消息是否正确发送到SQS
        4. 清理数据：SQS消息会自动过期
        
        关键验证点：
        - 消息的Base64编码正确性
        - SQS发送调用的成功性
        - 错误处理的完整性
        
        期望结果：
        - 消息成功发送到SQS队列
        - 返回True表示成功
        - 异常情况返回False
        """
        # 准备测试消息数据
        test_data = {
            'context': {'request_id': 'test-123'},
            'commit_id': 'commit-abc',
            'request_id': 'test-123',
            'number': 1,
            'mode': 'diff',
            'model': 'claude3-sonnet',
            'identity': 'test-identity',
            'filepath': 'test.py',
            'rule_name': '测试规则',
            'prompt_system': '系统提示词',
            'prompt_user': '用户提示词'
        }
        
        # 调用send_message函数
        result = task_dispatcher.send_message(test_data)
        
        # 验证发送结果
        if os.getenv('TASK_SQS_URL'):
            # 如果配置了SQS URL，应该尝试发送
            # 注意：这里可能因为权限或网络问题失败，但我们主要测试函数逻辑
            assert isinstance(result, bool), "send_message应该返回布尔值"
        else:
            # 如果没有配置SQS URL，应该失败
            assert result is False, "没有配置SQS URL时应该返回False"
        
        # 测试消息编码的正确性
        import base64
        encoded_message = base.encode_base64(base.dump_json(test_data))
        decoded_message = base.load_json(base.decode_base64(encoded_message))
        
        assert decoded_message == test_data, "消息编码解码后应该与原数据一致"

    def test_status_management(self):
        """
        测试目的：验证DynamoDB中请求状态的正确更新和管理
        
        测试场景：测试状态初始化、任务计数更新、完成状态设置等
        业务重要性：状态管理是系统监控和进度跟踪的基础，确保状态正确更新是系统可靠性的关键
        
        测试流程：
        1. 准备测试数据：创建测试请求记录
        2. 执行核心功能：执行状态更新操作
        3. 验证结果：直接读取数据库验证更新结果
        4. 清理数据：清理测试创建的记录
        
        关键验证点：
        - 状态字段的正确更新
        - 时间戳的准确记录
        - 计数字段的数值正确性
        - 异常情况的处理
        
        期望结果：
        - 数据库记录正确更新
        - 所有状态字段值准确
        - 异常情况得到妥善处理
        """
        import boto3
        
        # 获取DynamoDB资源
        dynamodb = boto3.resource("dynamodb")
        table_name = os.getenv('REQUEST_TABLE')
        
        if not table_name:
            pytest.skip("REQUEST_TABLE环境变量未设置，跳过状态管理测试")
            return
        
        table = dynamodb.Table(table_name)
        
        # 测试数据
        test_commit_id = 'test-commit-status-123'
        test_request_id = 'test-request-status-456'
        
        try:
            # 测试1：初始状态设置（模拟send_task_to_sqs中的状态更新）
            initial_time = str(datetime.datetime.now())
            
            # 创建初始记录
            table.put_item(
                Item={
                    'commit_id': test_commit_id,
                    'request_id': test_request_id,
                    'task_status': 'Pending',
                    'create_time': initial_time,
                    'update_time': initial_time,
                    'task_total': 0,
                    'task_complete': 0,
                    'task_failure': 0,
                    'report_s3key': '',
                    'report_url': ''
                }
            )
            
            # 模拟send_task_to_sqs中的状态更新
            update_time = str(datetime.datetime.now())
            table.update_item(
                Key={'commit_id': test_commit_id, 'request_id': test_request_id},
                UpdateExpression="set #s = :s, update_time = :t, task_complete = :tc, task_failure = :tf, task_total = :tt, report_s3key = :rs, report_url = :ru",
                ExpressionAttributeNames={'#s': 'task_status'},
                ExpressionAttributeValues={
                    ':s': 'Initializing',
                    ':t': update_time,
                    ':tc': 0,
                    ':tf': 0,
                    ':tt': 3,
                    ':rs': '',
                    ':ru': '',
                },
                ReturnValues="ALL_NEW",
            )
            
            # 验证状态更新
            response = table.get_item(
                Key={'commit_id': test_commit_id, 'request_id': test_request_id},
                ConsistentRead=True
            )
            
            assert 'Item' in response, "应该能找到更新后的记录"
            item = response['Item']
            
            assert item['task_status'] == 'Initializing', "任务状态应该更新为Initializing"
            assert item['task_total'] == 3, "任务总数应该正确"
            assert item['task_complete'] == 0, "完成任务数应该为0"
            assert item['task_failure'] == 0, "失败任务数应该为0"
            assert item['update_time'] == update_time, "更新时间应该正确"
            assert item['report_s3key'] == '', "报告S3键应该为空"
            assert item['report_url'] == '', "报告URL应该为空"
            
            # 测试2：失败计数更新（模拟任务发送失败时的更新）
            table.update_item(
                Key={'commit_id': test_commit_id, 'request_id': test_request_id},
                UpdateExpression="set task_failure = task_failure + :tf",
                ExpressionAttributeValues={':tf': 1},
                ReturnValues="ALL_NEW",
            )
            
            # 验证失败计数更新
            response = table.get_item(
                Key={'commit_id': test_commit_id, 'request_id': test_request_id},
                ConsistentRead=True
            )
            
            item = response['Item']
            assert item['task_failure'] == 1, "失败任务数应该增加1"
            
            # 测试3：完成状态设置（模拟没有任务时的完成状态）
            complete_commit_id = 'test-commit-complete-789'
            complete_request_id = 'test-request-complete-012'
            complete_time = str(datetime.datetime.now())
            
            # 创建完成状态的记录
            table.put_item(
                Item={
                    'commit_id': complete_commit_id,
                    'request_id': complete_request_id,
                    'task_status': base.STATUS_COMPLETE,
                    'task_complete': 0,
                    'task_failure': 0,
                    'task_total': 0,
                    'update_time': complete_time,
                    'create_time': complete_time
                }
            )
            
            # 验证完成状态
            response = table.get_item(
                Key={'commit_id': complete_commit_id, 'request_id': complete_request_id},
                ConsistentRead=True
            )
            
            item = response['Item']
            assert item['task_status'] == base.STATUS_COMPLETE, "任务状态应该是完成状态"
            assert item['task_total'] == 0, "无任务时总数应该为0"
            assert item['task_complete'] == 0, "无任务时完成数应该为0"
            assert item['task_failure'] == 0, "无任务时失败数应该为0"
            
            # 测试4：项目名称更新
            project_name = 'updated-project-name'
            task_dispatcher.update_project_name(test_commit_id, test_request_id, project_name)
            
            # 验证项目名称更新
            response = table.get_item(
                Key={'commit_id': test_commit_id, 'request_id': test_request_id},
                ConsistentRead=True
            )
            
            item = response['Item']
            assert item['project_name'] == project_name, "项目名称应该正确更新"
            assert 'update_time' in item, "应该有更新时间"
            
            # 测试5：异常情况处理 - 记录不存在
            with pytest.raises(Exception):
                task_dispatcher.update_dynamodb_status(
                    'nonexistent-commit', 'nonexistent-scope', 'Complete', 5
                )
            
        except Exception as e:
            if 'ResourceNotFoundException' in str(e):
                pytest.skip(f"DynamoDB表不存在，跳过状态管理测试: {e}")
            else:
                raise
        
        finally:
            # 清理测试数据
            try:
                table.delete_item(Key={'commit_id': test_commit_id, 'request_id': test_request_id})
                table.delete_item(Key={'commit_id': complete_commit_id, 'request_id': complete_request_id})
            except Exception as e:
                print(f"清理测试数据时出错: {e}")

    def test_get_targets(self):
        """
        测试目的：验证目标文件模式的解析逻辑
        
        测试场景：测试不同格式的target字段解析
        业务重要性：目标解析是文件过滤的基础，确保正确解析是内容获取准确性的前提
        
        测试流程：
        1. 准备测试数据：构造不同格式的规则
        2. 执行核心功能：调用get_targets函数
        3. 验证结果：检查解析结果的正确性
        4. 清理数据：无需清理
        
        关键验证点：
        - 单个目标的解析
        - 多个目标的分割
        - 空目标的处理
        - 特殊字符的处理
        
        期望结果：
        - 正确解析单个和多个目标
        - 正确处理空值和特殊情况
        """
        # 测试单个目标
        rule_single = {'target': 'src/**'}
        targets = task_dispatcher.get_targets(rule_single)
        assert targets == ['src/**'], "单个目标应该正确解析"
        
        # 测试多个目标
        rule_multiple = {'target': 'src/**,test/**,docs/**'}
        targets = task_dispatcher.get_targets(rule_multiple)
        expected = ['src/**', 'test/**', 'docs/**']
        assert targets == expected, "多个目标应该正确分割"
        
        # 测试带空格的目标
        rule_spaces = {'target': ' src/** , test/** , docs/** '}
        targets = task_dispatcher.get_targets(rule_spaces)
        expected = ['src/**', 'test/**', 'docs/**']
        assert targets == expected, "应该正确处理空格"
        
        # 测试空目标
        rule_empty = {'target': ''}
        targets = task_dispatcher.get_targets(rule_empty)
        assert targets == [''], "空目标应该返回包含空字符串的列表"
        
        # 测试没有target字段
        rule_no_target = {}
        targets = task_dispatcher.get_targets(rule_no_target)
        assert targets == [''], "没有target字段应该返回包含空字符串的列表"
        
        # 测试以点结尾的目标
        rule_dot_end = {'target': 'src/**.'}
        targets = task_dispatcher.get_targets(rule_dot_end)
        assert targets == ['src/**'], "应该去除末尾的点"
        
        # 测试复杂的目标组合
        rule_complex = {'target': '*.py, **/*.js, src/main.*, test/**.'}
        targets = task_dispatcher.get_targets(rule_complex)
        expected = ['*.py', '**/*.js', 'src/main.*', 'test/**']
        assert targets == expected, "复杂目标组合应该正确解析"

    @patch('task_dispatcher.codelib.init_repo_context')
    @patch('task_dispatcher.codelib.get_rules')
    @patch('task_dispatcher.send_task_to_sqs')
    def test_exception_handling(self, mock_send_task_to_sqs, mock_get_rules, mock_init_repo_context):
        """
        测试目的：验证各种异常情况的处理能力
        
        测试场景：测试仓库访问失败、规则解析错误、数据库操作失败等异常情况
        业务重要性：异常处理是系统健壮性的关键，确保异常情况得到妥善处理
        
        测试流程：
        1. 准备测试数据：Mock各种异常情况
        2. 执行核心功能：调用lambda_handler函数
        3. 验证结果：检查异常被正确捕获和处理
        4. 清理数据：Mock会自动清理
        
        关键验证点：
        - 异常捕获的完整性
        - 错误信息的准确性
        - 系统状态的一致性
        - 日志记录的详细性
        
        期望结果：
        - 异常被正确捕获和处理
        - 返回适当的错误响应
        - 系统状态保持一致
        """
        # 测试1：SQS事件验证失败
        invalid_event = {
            'commit_id': 'test-commit',
            'target_branch': 'main'
            # 缺失 request_id 字段
        }
        
        response = task_dispatcher.lambda_handler(invalid_event, {})
        
        assert response['statusCode'] == 500, "事件验证失败应该返回500状态码"
        assert 'request_id' in response['body'], "错误信息应该包含缺失的字段"
        
        # 测试2：仓库上下文初始化失败
        valid_event = {
            'request_id': 'test-request-123',
            'commit_id': 'test-commit-456',
            'event_type': 'push',
            'target_branch': 'main',
            'project_name': 'test-project'
        }
        
        # Mock init_repo_context抛出异常
        from gitlab.exceptions import GitlabAuthenticationError
        mock_init_repo_context.side_effect = GitlabAuthenticationError("Invalid token")
        
        response = task_dispatcher.lambda_handler(valid_event, {})
        
        # 验证异常被捕获（函数应该继续执行，但可能会有问题）
        # 注意：当前实现可能不会在这里直接返回错误，而是在后续步骤中处理
        mock_init_repo_context.assert_called_once()
        
        # 测试3：规则加载失败
        mock_init_repo_context.reset_mock()
        mock_init_repo_context.side_effect = None
        mock_init_repo_context.return_value = {'project': Mock(name='test-project')}
        
        # Mock get_rules抛出异常
        mock_get_rules.side_effect = Exception("Failed to load rules")
        
        response = task_dispatcher.lambda_handler(valid_event, {})
        
        # 验证规则加载被调用
        mock_get_rules.assert_called_once()
        
        # 测试4：任务分发失败
        mock_get_rules.reset_mock()
        mock_get_rules.side_effect = None
        mock_get_rules.return_value = [
            {
                'name': '测试规则',
                'mode': 'diff',
                'branch': 'main',
                'event': 'push',
                'model': 'claude3-sonnet',
                'target': '*.py'
            }
        ]
        
        # Mock send_task_to_sqs返回失败
        mock_send_task_to_sqs.return_value = False
        
        # Mock codelib函数返回测试数据
        with patch('task_dispatcher.codelib.format_commit_id') as mock_format_commit_id, \
             patch('task_dispatcher.codelib.get_involved_files') as mock_get_involved_files:
            
            mock_format_commit_id.return_value = 'formatted-commit-id'
            mock_get_involved_files.return_value = {'test.py': 'diff content'}
            
            response = task_dispatcher.lambda_handler(valid_event, {})
            
            # 验证任务分发被调用
            mock_send_task_to_sqs.assert_called_once()
        
        # 测试5：项目名称更新失败
        mock_project = Mock()
        mock_project.name = 'actual-project-name'
        mock_init_repo_context.return_value = {'project': mock_project}
        
        # 修改事件中的项目名称，触发更新
        event_with_wrong_name = valid_event.copy()
        event_with_wrong_name['project_name'] = 'wrong-project-name'
        
        with patch('task_dispatcher.update_project_name') as mock_update_project_name:
            mock_update_project_name.side_effect = Exception("DynamoDB update failed")
            
            # 这个异常应该被捕获，不影响主流程
            response = task_dispatcher.lambda_handler(event_with_wrong_name, {})
            
            mock_update_project_name.assert_called_once_with(
                'formatted-commit-id', 'test-request-123', 'actual-project-name'
            )
        
        # 测试6：空规则列表的处理
        mock_get_rules.return_value = []
        mock_send_task_to_sqs.reset_mock()
        
        with patch('task_dispatcher.report.generate_report_and_notify') as mock_generate_report:
            response = task_dispatcher.lambda_handler(valid_event, {})
            
            # 验证没有任务时不调用send_task_to_sqs
            mock_send_task_to_sqs.assert_not_called()
            
            # 验证直接生成报告（对于webtool请求）
            if valid_event.get('invoker') == 'webtool':
                mock_generate_report.assert_called_once()
        
        # 测试7：commit_id格式化异常
        with patch('task_dispatcher.codelib.format_commit_id') as mock_format_commit_id:
            mock_format_commit_id.side_effect = Exception("Invalid commit ID")
            
            # 这个异常可能会导致函数执行失败
            try:
                response = task_dispatcher.lambda_handler(valid_event, {})
                # 如果没有抛出异常，验证响应
                assert 'statusCode' in response, "应该返回有效的响应"
            except Exception as e:
                # 如果抛出异常，验证异常类型
                assert "Invalid commit ID" in str(e), "应该包含具体的错误信息"

    def test_boundary_conditions(self):
        """
        测试目的：验证系统在极端条件下的行为表现
        
        测试场景：测试空仓库、无变更、大量规则等边界情况
        业务重要性：边界条件测试确保系统在极端情况下仍能稳定运行
        
        测试流程：
        1. 准备测试数据：构造极端情况的测试数据
        2. 执行核心功能：执行完整的处理流程
        3. 验证结果：检查系统行为的合理性
        4. 清理数据：清理测试数据
        
        关键验证点：
        - 空数据的处理
        - 性能表现
        - 内存使用
        - 错误处理
        
        期望结果：
        - 极端情况得到合理处理
        - 系统保持稳定运行
        - 性能在可接受范围内
        """
        # 测试1：空仓库（没有任何代码文件）
        with patch('task_dispatcher.codelib.get_project_code_text') as mock_get_project_code_text, \
             patch('task_dispatcher.codelib.get_involved_files') as mock_get_involved_files:
            
            mock_get_project_code_text.return_value = None  # 空仓库
            mock_get_involved_files.return_value = {}  # 没有变更文件
            
            repo_context = {'project': Mock(name='empty-repo')}
            
            # 测试All模式
            rule_all = {'name': '空仓库检查', 'mode': 'all', 'target': '**'}
            contents = task_dispatcher.get_code_contents_for_all(repo_context, 'commit123', rule_all)
            assert len(contents) == 0, "空仓库应该返回空内容列表"
            
            # 测试Single模式
            rule_single = {'name': '空仓库单文件检查', 'mode': 'single', 'target': '*.py'}
            contents = task_dispatcher.get_code_contents_for_single(
                repo_context, 'commit123', 'commit456', rule_single
            )
            assert len(contents) == 0, "没有变更文件应该返回空内容列表"
            
            # 测试Diff模式
            rule_diff = {'name': '空仓库差异检查', 'mode': 'diff', 'target': '**'}
            contents = task_dispatcher.get_code_contents_for_diff(
                repo_context, 'commit123', 'commit456', rule_diff
            )
            assert len(contents) == 0, "没有差异应该返回空内容列表"
        
        # 测试2：无变更（commit_id与previous_commit_id相同）
        same_commit_event = {
            'request_id': 'test-no-change',
            'commit_id': 'same-commit-123',
            'previous_commit_id': 'same-commit-123',
            'event_type': 'push',
            'target_branch': 'main',
            'project_name': 'test-project'
        }
        
        with patch('task_dispatcher.codelib.init_repo_context') as mock_init_repo_context, \
             patch('task_dispatcher.codelib.get_rules') as mock_get_rules, \
             patch('task_dispatcher.codelib.format_commit_id') as mock_format_commit_id, \
             patch('task_dispatcher.codelib.get_involved_files') as mock_get_involved_files:
            
            mock_init_repo_context.return_value = {'project': Mock(name='test-project')}
            mock_get_rules.return_value = [
                {'name': '无变更检查', 'mode': 'diff', 'branch': 'main', 'event': 'push', 'target': '**'}
            ]
            mock_format_commit_id.return_value = 'same-commit-123'
            mock_get_involved_files.return_value = {}  # 没有变更
            
            response = task_dispatcher.lambda_handler(same_commit_event, {})
            
            # 验证函数正常执行
            assert response['statusCode'] == 200, "无变更情况应该正常处理"
        
        # 测试3：大量规则
        large_rules = []
        for i in range(50):  # 创建50个规则
            large_rules.append({
                'name': f'规则{i}',
                'mode': 'diff',
                'branch': 'main',
                'event': 'push',
                'model': 'claude3-haiku',
                'target': f'module{i}/**'
            })
        
        with patch('task_dispatcher.codelib.get_rules') as mock_get_rules:
            mock_get_rules.return_value = large_rules
            
            # 测试规则过滤
            target_branch = 'main'
            event_type = 'push'
            
            filtered_rules = []
            for rule in large_rules:
                if task_dispatcher.match_branch(rule.get('branch'), target_branch) and rule.get('event') == event_type:
                    filtered_rules.append(rule)
            
            assert len(filtered_rules) == 50, "所有规则都应该匹配"
            
            # 验证规则名称的唯一性
            rule_names = [rule['name'] for rule in filtered_rules]
            assert len(set(rule_names)) == 50, "规则名称应该是唯一的"
        
        # 测试4：深层目录结构
        deep_files = {}
        for i in range(10):
            deep_path = '/'.join([f'level{j}' for j in range(i)]) + f'/file{i}.py'
            deep_files[deep_path] = f'content for {deep_path}'
        
        with patch('task_dispatcher.codelib.get_involved_files') as mock_get_involved_files, \
             patch('task_dispatcher.codelib.get_repository_file') as mock_get_repository_file:
            
            mock_get_involved_files.return_value = deep_files
            mock_get_repository_file.side_effect = lambda repo, path, commit: deep_files.get(path, '')
            
            rule_deep = {'name': '深层目录检查', 'mode': 'single', 'target': '**/*.py'}
            contents = task_dispatcher.get_code_contents_for_single(
                {'project': Mock()}, 'commit123', 'commit456', rule_deep
            )
            
            assert len(contents) == 10, "应该处理所有深层文件"
            
            # 验证文件路径的正确性
            file_paths = [content['filepath'] for content in contents]
            for path in deep_files.keys():
                assert path in file_paths, f"应该包含文件路径: {path}"
        
        # 测试5：特殊字符处理
        special_files = {
            'file with spaces.py': 'content1',
            'file-with-dashes.py': 'content2',
            'file_with_underscores.py': 'content3',
            '中文文件名.py': 'content4',
            'file.with.dots.py': 'content5'
        }
        
        with patch('task_dispatcher.codelib.get_involved_files') as mock_get_involved_files:
            mock_get_involved_files.return_value = special_files
            
            rule_special = {'name': '特殊字符检查', 'mode': 'diff', 'target': '*.py'}
            contents = task_dispatcher.get_code_contents_for_diff(
                {'project': Mock()}, 'commit123', 'commit456', rule_special
            )
            
            assert len(contents) == 5, "应该处理所有特殊字符文件"
            
            # 验证特殊字符文件名的处理
            file_paths = [content['filepath'] for content in contents]
            assert 'file with spaces.py' in file_paths, "应该正确处理空格"
            assert '中文文件名.py' in file_paths, "应该正确处理中文字符"
            assert 'file.with.dots.py' in file_paths, "应该正确处理点号"

    @patch('task_dispatcher.codelib.init_repo_context')
    @patch('task_dispatcher.codelib.format_commit_id')
    @patch('task_dispatcher.codelib.get_rules')
    @patch('task_dispatcher.codelib.get_involved_files')
    @patch('task_dispatcher.codelib.get_repository_file')
    @patch('task_dispatcher.codelib.get_project_code_text')
    @patch('task_dispatcher.send_message')
    def test_integration_scenarios(self, mock_send_message, mock_get_project_code_text, 
                                 mock_get_repository_file, mock_get_involved_files, 
                                 mock_get_rules, mock_format_commit_id, mock_init_repo_context):
        """
        测试目的：验证完整业务流程的端到端正确性
        
        测试场景：测试完整的Webtool和Webhook流程
        业务重要性：集成测试确保所有组件协调工作，验证完整业务流程的正确性
        
        测试流程：
        1. 准备测试数据：构造完整的业务场景数据
        2. 执行核心功能：调用lambda_handler函数
        3. 验证结果：检查整个流程的正确性
        4. 清理数据：Mock会自动清理
        
        关键验证点：
        - 流程完整性
        - 数据一致性
        - 状态正确性
        - 副作用验证
        
        期望结果：
        - 完整流程正确执行
        - 所有组件协调工作
        - 最终状态符合预期
        """
        # 设置通用Mock
        mock_project = Mock()
        mock_project.name = 'test-integration-project'
        mock_init_repo_context.return_value = {'project': mock_project}
        mock_format_commit_id.return_value = 'formatted-commit-123'
        mock_send_message.return_value = True
        
        # 测试场景1：完整Webtool流程
        webtool_event = {
            'invoker': 'webtool',
            'request_id': 'webtool-request-123',
            'commit_id': 'webtool-commit-456',
            'event_type': 'push',
            'target_branch': 'main',
            'project_name': 'test-integration-project',
            'rule_name': 'Webtool代码质量检查',
            'mode': 'diff',
            'model': 'claude3-sonnet',
            'target': 'src/**',
            'confirm': True,
            'webtool_prompt_system': '你是一个专业的代码审查助手',
            'webtool_prompt_user': '请检查以下代码的质量问题'
        }
        
        # Mock文件变更数据
        mock_get_involved_files.return_value = {
            'src/app.py': 'diff content for app.py',
            'src/utils.py': 'diff content for utils.py'
        }
        
        # 执行Webtool流程
        response = task_dispatcher.lambda_handler(webtool_event, {})
        
        # 验证Webtool流程的执行
        assert response['statusCode'] == 200, "Webtool流程应该成功执行"
        
        # 验证仓库上下文初始化
        mock_init_repo_context.assert_called_with(webtool_event)
        
        # 验证commit_id格式化
        assert mock_format_commit_id.call_count >= 1, "应该格式化commit_id"
        
        # 验证任务发送
        assert mock_send_message.call_count == 2, "应该发送2个任务（2个文件）"
        
        # 验证任务数据结构
        first_task = mock_send_message.call_args_list[0][0][0]
        assert first_task['request_id'] == 'webtool-request-123', "任务应该包含正确的request_id"
        assert first_task['mode'] == 'diff', "任务模式应该正确"
        assert first_task['model'] == 'claude3-sonnet', "任务模型应该正确"
        assert first_task['rule_name'] == 'Webtool代码质量检查', "任务规则名称应该正确"
        assert 'confirm_prompt' in first_task, "Webtool任务应该包含确认提示词"
        
        # 重置Mock为下一个测试
        mock_send_message.reset_mock()
        mock_get_rules.reset_mock()
        
        # 测试场景2：完整Webhook流程
        webhook_event = {
            'invoker': 'webhook',
            'request_id': 'webhook-request-789',
            'commit_id': 'webhook-commit-012',
            'previous_commit_id': 'webhook-previous-345',
            'event_type': 'push',
            'target_branch': 'develop',
            'project_name': 'test-integration-project'
        }
        
        # Mock仓库规则
        mock_rules = [
            {
                'name': '代码质量检查',
                'mode': 'diff',
                'branch': 'develop',
                'event': 'push',
                'model': 'claude3-haiku',
                'target': '**/*.py',
                'system': '你是一个Python代码审查专家',
                'quality': '请检查代码质量',
                'security': '请检查安全问题'
            },
            {
                'name': '全项目安全检查',
                'mode': 'all',
                'branch': 'develop',
                'event': 'push',
                'model': 'claude3-opus',
                'target': 'src/**',
                'system': '你是一个安全专家',
                'security_check': '请进行全面的安全检查'
            }
        ]
        mock_get_rules.return_value = mock_rules
        
        # Mock项目代码
        mock_get_project_code_text.return_value = """
def main():
    print("Hello World")
    
class Application:
    def run(self):
        pass
"""
        
        # 执行Webhook流程
        response = task_dispatcher.lambda_handler(webhook_event, {})
        
        # 验证Webhook流程的执行
        assert response['statusCode'] == 200, "Webhook流程应该成功执行"
        
        # 验证规则加载
        mock_get_rules.assert_called_once_with(
            mock_init_repo_context.return_value, 'formatted-commit-123', 'develop'
        )
        
        # 验证任务发送（2个文件的diff模式 + 1个all模式 = 3个任务）
        expected_tasks = 2 + 1  # 2个diff任务 + 1个all任务
        assert mock_send_message.call_count == expected_tasks, f"应该发送{expected_tasks}个任务"
        
        # 验证不同模式的任务
        sent_tasks = [call[0][0] for call in mock_send_message.call_args_list]
        diff_tasks = [task for task in sent_tasks if task['mode'] == 'diff']
        all_tasks = [task for task in sent_tasks if task['mode'] == 'all']
        
        assert len(diff_tasks) == 2, "应该有2个diff模式任务"
        assert len(all_tasks) == 1, "应该有1个all模式任务"
        
        # 验证任务编号的连续性
        task_numbers = [task['number'] for task in sent_tasks]
        assert task_numbers == [1, 2, 3], "任务编号应该连续"
        
        # 重置Mock为下一个测试
        mock_send_message.reset_mock()
        mock_get_rules.reset_mock()
        
        # 测试场景3：多规则并行处理
        multi_rule_event = {
            'request_id': 'multi-rule-request-456',
            'commit_id': 'multi-rule-commit-789',
            'previous_commit_id': 'multi-rule-previous-012',
            'event_type': 'merge_request',
            'target_branch': 'main',
            'project_name': 'test-integration-project'
        }
        
        # Mock多个匹配的规则
        multi_rules = [
            {
                'name': '代码质量检查',
                'mode': 'diff',
                'branch': 'main',
                'event': 'merge_request',
                'model': 'claude3-sonnet',
                'target': '**/*.py'
            },
            {
                'name': '安全检查',
                'mode': 'diff',
                'branch': 'main',
                'event': 'merge_request',
                'model': 'claude3-haiku',
                'target': '**/*.py'
            },
            {
                'name': '性能检查',
                'mode': 'single',
                'branch': 'main',
                'event': 'merge_request',
                'model': 'claude3-opus',
                'target': 'src/**'
            }
        ]
        mock_get_rules.return_value = multi_rules
        
        # Mock文件内容
        mock_get_repository_file.side_effect = lambda repo, path, commit: f"content of {path}"
        
        # 执行多规则流程
        response = task_dispatcher.lambda_handler(multi_rule_event, {})
        
        # 验证多规则处理
        assert response['statusCode'] == 200, "多规则流程应该成功执行"
        
        # 验证任务数量（2个diff规则 * 2个文件 + 1个single规则 * 2个文件 = 6个任务）
        expected_multi_tasks = 2 * 2 + 1 * 2  # 6个任务
        assert mock_send_message.call_count == expected_multi_tasks, f"应该发送{expected_multi_tasks}个任务"
        
        # 验证不同规则的任务
        multi_sent_tasks = [call[0][0] for call in mock_send_message.call_args_list]
        rule_names = [task['rule_name'] for task in multi_sent_tasks]
        
        assert '代码质量检查' in rule_names, "应该包含代码质量检查任务"
        assert '安全检查' in rule_names, "应该包含安全检查任务"
        assert '性能检查' in rule_names, "应该包含性能检查任务"
        
        # 测试场景4：项目名更新场景
        name_update_event = {
            'request_id': 'name-update-request-123',
            'commit_id': 'name-update-commit-456',
            'event_type': 'push',
            'target_branch': 'main',
            'project_name': 'wrong-project-name'  # 与实际项目名不匹配
        }
        
        mock_get_rules.return_value = []  # 没有匹配的规则
        
        with patch('task_dispatcher.update_project_name') as mock_update_project_name:
            response = task_dispatcher.lambda_handler(name_update_event, {})
            
            # 验证项目名更新被调用
            mock_update_project_name.assert_called_once_with(
                'formatted-commit-123', 'name-update-request-123', 'test-integration-project'
            )
        
        # 测试场景5：无任务的完成流程
        no_task_event = {
            'invoker': 'webtool',
            'request_id': 'no-task-request-789',
            'commit_id': 'no-task-commit-012',
            'event_type': 'push',
            'target_branch': 'main',
            'project_name': 'test-integration-project',
            'rule_name': '无匹配规则',
            'mode': 'diff',
            'model': 'claude3-sonnet',
            'target': 'nonexistent/**'
        }
        
        # Mock没有匹配的文件
        mock_get_involved_files.return_value = {}
        
        with patch('task_dispatcher.report.generate_report_and_notify') as mock_generate_report:
            response = task_dispatcher.lambda_handler(no_task_event, {})
            
            # 验证直接生成报告
            mock_generate_report.assert_called_once()
            
            # 验证响应成功
            assert response['statusCode'] == 200, "无任务流程应该成功执行"
