#!/usr/bin/env python3
"""
集成测试验证框架
提供可复用的验证逻辑，支持不同类型的代码评审测试
"""

import json
import time
import boto3
from datetime import datetime, timedelta

class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_checks = 0
    
    def check(self, condition, success_msg, error_msg):
        self.total_checks += 1
        if condition:
            self.success_count += 1
            print(f"✓ {success_msg}")
        else:
            self.errors.append(error_msg)
            print(f"❌ {error_msg}")
    
    def info(self, msg):
        print(f"📋 {msg}")
    
    def warn(self, msg):
        self.warnings.append(msg)
        print(f"⚠️ {msg}")
    
    def is_success(self):
        return len(self.errors) == 0
    
    def summary(self):
        print(f"\n=== 验证总结 ===")
        print(f"总检查项: {self.total_checks}")
        print(f"成功: {self.success_count}")
        print(f"失败: {len(self.errors)}")
        print(f"警告: {len(self.warnings)}")
        
        if self.errors:
            print(f"\n失败项目:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n警告项目:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if self.is_success():
            print(f"\n✅ 所有验证通过")
        else:
            print(f"\n❌ 验证失败")

class DatabaseValidator:
    """数据库验证器"""
    
    def __init__(self, config):
        self.config = config
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.request_table = self.dynamodb.Table(config['aws']['request_table'])
        self.task_table = self.dynamodb.Table(config['aws']['task_table'])
    
    def find_latest_request_record(self, expected_commit_id):
        """查找最新的request记录"""
        response = self.request_table.scan(ConsistentRead=True)
        request_items = response['Items']
        
        # 查找匹配commit_id的记录
        matching_requests = [r for r in request_items if r.get('commit_id') == expected_commit_id]
        
        if not matching_requests:
            return None
        
        # 优先选择task_total > 0的记录（说明触发了评审）
        review_requests = [r for r in matching_requests if int(r.get('task_total', 0)) > 0]
        
        if review_requests:
            # 按创建时间排序，取最新的
            review_requests.sort(key=lambda x: x.get('create_time', ''), reverse=True)
            return review_requests[0]
        else:
            # 如果没有触发评审的记录，返回最新的记录
            matching_requests.sort(key=lambda x: x.get('create_time', ''), reverse=True)
            return matching_requests[0]

    def wait_for_task_allocation(self, expected_commit_id, timeout=30):
        """等待task分配完成（30秒内）"""
        print(f"⏳ 等待task分配完成（最多{timeout}秒）...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            print(f"\n🔍 查询Request表 - commit_id: '{expected_commit_id}'")
            request = self.find_latest_request_record(expected_commit_id)
            if request:
                task_total = request.get('task_total', 0)
                print(f"🔍 查询结果: 找到记录，task_total = {task_total}")
                if int(task_total) > 0:
                    print(f"✅ Task分配完成，task_total = {task_total}")
                    return request
            else:
                print(f"🔍 查询结果: 未找到匹配的记录")
            
            print(".", end="", flush=True)
            time.sleep(2)
        
        print(f"\n⚠️ Task分配超时（{timeout}秒）")
        return self.find_latest_request_record(expected_commit_id)
    
    def wait_for_task_completion(self, request_record, timeout=300):
        """等待所有task执行完成（5分钟内）"""
        if not request_record:
            return None
            
        request_id = request_record['request_id']
        commit_id = request_record['commit_id']
        task_total = int(request_record.get('task_total', 0))
        
        if task_total == 0:
            print("ℹ️ 无需等待task完成（task_total = 0）")
            return request_record
        
        print(f"⏳ 等待{task_total}个task执行完成（最多{timeout//60}分钟）...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 使用正确的复合主键
            print(f"\n🔍 查询Request表 - commit_id: '{commit_id}', request_id: '{request_id}'")
            response = self.request_table.get_item(
                Key={
                    'commit_id': commit_id,
                    'request_id': request_id
                },
                ConsistentRead=True
            )
            
            if 'Item' not in response:
                print("🔍 查询结果: 未找到Request记录")
                break
                
            current_request = response['Item']
            task_status = current_request.get('task_status', '')
            task_complete = current_request.get('task_complete', '0')
            task_total = current_request.get('task_total', '0')
            print(f"🔍 查询结果: task_status={task_status}, task_complete={task_complete}, task_total={task_total}")
            task_complete = int(current_request.get('task_complete', 0))
            
            if task_status == 'Complete':
                print(f"\n✅ 所有task执行完成，task_complete = {task_complete}")
                return current_request
            
            print(".", end="", flush=True)
            time.sleep(5)
        
        print(f"\n⚠️ Task执行超时（{timeout//60}分钟）")
        response = self.request_table.get_item(
            Key={
                'commit_id': commit_id,
                'request_id': request_id
            },
            ConsistentRead=True
        )
        return response.get('Item') if 'Item' in response else request_record
        """查找最新的request记录"""
        response = self.request_table.scan(ConsistentRead=True)
        request_items = response['Items']
        
        # 查找匹配commit_id的记录
        matching_requests = [r for r in request_items if r.get('commit_id') == expected_commit_id]
        
        if not matching_requests:
            return None
        
        # 优先选择task_total > 0的记录（说明触发了评审）
        review_requests = [r for r in matching_requests if int(r.get('task_total', 0)) > 0]
        
        if review_requests:
            # 按创建时间排序，取最新的
            review_requests.sort(key=lambda x: x.get('create_time', ''), reverse=True)
            return review_requests[0]
        else:
            # 如果没有触发评审的记录，返回最新的记录
            matching_requests.sort(key=lambda x: x.get('create_time', ''), reverse=True)
            return matching_requests[0]
    
    def validate_request_table(self, expected_commit_id, expected_project_name, expected_task_count, result):
        """验证request表数据"""
        print("\n=== 验证Request表 ===")
        
        request = self.find_latest_request_record(expected_commit_id)
        
        if not request:
            result.check(False, "", f"未找到commit_id为 {expected_commit_id} 的request记录")
            return None
        
        result.info(f"找到匹配的request记录: {request.get('request_id')}")
        result.info(f"创建时间: {request.get('create_time')}")
        
        # 验证基本字段
        self._validate_basic_request_fields(request, expected_commit_id, expected_project_name, result)
        
        # 验证任务相关字段
        self._validate_task_fields(request, expected_task_count, result)
        
        return request
    
    def _validate_basic_request_fields(self, request, expected_commit_id, expected_project_name, result):
        """验证request表基本字段"""
        # 打印原始数据
        result.info("Request表原始数据:")
        print(json.dumps(request, indent=2, default=str))
        
        # 验证request_id格式
        request_id = request.get('request_id', '')
        result.check(
            'gitlab' in request_id or 'github' in request_id,
            f"request_id格式正确: {request_id}",
            f"request_id格式错误: {request_id}"
        )
        
        # 验证commit_id
        result.check(
            request.get('commit_id') == expected_commit_id,
            f"commit_id正确: {expected_commit_id}",
            f"commit_id错误: 期望 {expected_commit_id}, 实际 {request.get('commit_id')}"
        )
        
        # 验证project_name
        result.check(
            request.get('project_name') == expected_project_name,
            f"project_name正确: {expected_project_name}",
            f"project_name错误: 期望 {expected_project_name}, 实际 {request.get('project_name')}"
        )
    
    def _validate_task_fields(self, request, expected_task_count, result):
        """验证任务相关字段"""
        task_total = int(request.get('task_total', 0))
        task_complete = int(request.get('task_complete', 0))
        task_failure = int(request.get('task_failure', 0))
        task_status = request.get('task_status', '')
        
        # 验证task_total
        if expected_task_count is not None:
            result.check(
                task_total == expected_task_count,
                f"task_total正确: {task_total}",
                f"task_total错误: 期望 {expected_task_count}, 实际 {task_total}"
            )
        
        # 根据task_total判断是否应该有任务
        if task_total == 0:
            self._validate_no_task_scenario(request, result)
        elif task_status == 'Complete':
            self._validate_completed_task_scenario(request, result)
        else:
            self._validate_processing_task_scenario(request, result)
        
        # 验证task_failure
        result.check(
            task_failure == 0,
            f"task_failure正确: {task_failure}",
            f"task_failure错误: 期望 0, 实际 {task_failure}"
        )
        
        # 打印状态信息
        result.info(f"task_status: {task_status}")
        result.info(f"task_total: {task_total}")
    
    def _validate_no_task_scenario(self, request, result):
        """验证无任务场景"""
        task_complete = int(request.get('task_complete', 0))
        
        result.check(
            task_complete == 0,
            f"task_complete正确（无任务）: {task_complete}",
            f"task_complete错误: 期望 0, 实际 {task_complete}"
        )
        
        # 验证报告字段应为空
        report_url = request.get('report_url', '')
        report_s3key = request.get('report_s3key', '')
        
        result.check(
            not report_url,
            "report_url为空（无任务）",
            f"report_url应为空: {report_url}"
        )
        
        result.check(
            not report_s3key,
            "report_s3key为空（无任务）",
            f"report_s3key应为空: {report_s3key}"
        )
    
    def _validate_completed_task_scenario(self, request, result):
        """验证任务完成场景"""
        task_total = int(request.get('task_total', 0))
        task_complete = int(request.get('task_complete', 0))
        
        result.check(
            task_complete == task_total,
            f"task_complete正确（任务已完成）: {task_complete}",
            f"task_complete错误: 期望 {task_total}, 实际 {task_complete}"
        )
        
        # 验证报告字段应该有值
        report_url = request.get('report_url', '')
        report_s3key = request.get('report_s3key', '')
        
        result.check(
            bool(report_url) and report_url.startswith('http'),
            f"report_url有效: {len(report_url)}字符",
            f"report_url无效: {report_url}"
        )
        
        result.check(
            len(report_s3key) > 10,
            f"report_s3key有效: {len(report_s3key)}字符",
            f"report_s3key无效: {len(report_s3key)}字符"
        )
    
    def _validate_processing_task_scenario(self, request, result):
        """验证任务进行中场景"""
        task_total = int(request.get('task_total', 0))
        task_complete = int(request.get('task_complete', 0))
        
        result.check(
            task_complete < task_total,
            f"task_complete正确（任务进行中）: {task_complete}",
            f"task_complete错误: {task_complete}"
        )
        
        # 验证报告字段应为空
        report_url = request.get('report_url', '')
        report_s3key = request.get('report_s3key', '')
        
        result.check(
            not report_url,
            "report_url为空（任务未完成）",
            f"report_url应为空: {report_url}"
        )
        
        result.check(
            not report_s3key,
            "report_s3key为空（任务未完成）",
            f"report_s3key应为空: {report_s3key}"
        )
    
    def validate_task_table(self, request_record, result):
        """验证task表数据"""
        if not request_record:
            return []
        
        print("\n=== 验证Task表 ===")
        
        request_id = request_record['request_id']
        expected_task_count = int(request_record.get('task_total', 0))
        
        # 等待Task表记录创建（最多60秒，使用强一致性读取）
        print(f"⏳ 等待Task表记录创建（最多60秒）...")
        print(f"🔍 期望任务数: {expected_task_count}")
        start_time = time.time()
        matching_tasks = []
        
        while time.time() - start_time < 60:
            # 使用query直接根据request_id查询，比scan快得多
            print(f"\n🔍 查询Task表 - request_id: '{request_id}'")
            response = self.task_table.query(
                KeyConditionExpression='request_id = :request_id',
                ExpressionAttributeValues={':request_id': request_id},
                ConsistentRead=True
            )
            matching_tasks = response['Items']
            print(f"🔍 查询结果: 找到 {len(matching_tasks)} 条Task记录")
            if len(matching_tasks) > 0:
                for i, task in enumerate(matching_tasks):
                    number = task.get('number', 'N/A')
                    succ = task.get('succ', 'N/A')
                    print(f"  - Task {number}: succ={succ}")
            else:
                print("  - 无Task记录")
            
            print(f"🔍 退出条件: {len(matching_tasks)} >= {expected_task_count} = {len(matching_tasks) >= expected_task_count}")
            
            if len(matching_tasks) >= expected_task_count:
                print(f"✅ 找到{len(matching_tasks)}条Task记录")
                break
                
            print(".", end="", flush=True)
            time.sleep(3)  # 增加等待间隔
        
        if len(matching_tasks) < expected_task_count:
            print(f"\n⚠️ Task记录数量不足，继续验证现有记录")
        
        result.check(
            len(matching_tasks) == expected_task_count,
            f"task数量正确: {len(matching_tasks)}条",
            f"task数量错误: 期望 {expected_task_count}, 实际 {len(matching_tasks)}条"
        )
        
        for i, task in enumerate(matching_tasks):
            print(f"\n--- Task {i+1} ---")
            self._validate_single_task(task, request_id, result)
        
        return matching_tasks
    
    def _validate_single_task(self, task, request_id, result):
        """验证单个task记录"""
        # 打印原始数据
        result.info("Task原始数据:")
        print(json.dumps(task, indent=2, default=str))
        
        # 验证number字段（相当于task_id）
        number = task.get('number', '')
        result.check(
            bool(number) and str(number).isdigit(),
            f"number字段存在且有效: {number}",
            f"number字段无效: {number}"
        )
        
        result.check(
            task.get('request_id') == request_id,
            "request_id匹配",
            "request_id不匹配"
        )
        
        # 验证model - 根据expected_model参数验证
        model = task.get('model', '')
        mode = task.get('mode', '')

        if hasattr(self, 'expected_model') and self.expected_model:
            # 如果指定了expected_model，进行精确匹配
            result.check(
                model == self.expected_model,
                f"model正确: {model}",
                f"model错误: 期望 {self.expected_model}, 实际 {model}"
            )
        else:
            # 否则使用通用验证 - 检查是否是合法的 Claude 模型名称
            valid_models = [
                'claude3-sonnet', 'claude3-haiku', 'claude3-opus',
                'claude3.5-sonnet', 'claude3.5-haiku',
                'claude3.7-sonnet',
                'claude4-sonnet', 'claude4-opus',
                'claude4.5-sonnet'
            ]
            result.check(
                model in valid_models,
                f"model有效: {model}",
                f"model无效: {model} (不在已知模型列表中)"
            )
        
        # 验证succ字段（任务状态）
        succ = task.get('succ')
        if succ is None:
            result.info("succ字段不存在（任务可能还在进行中）")
        elif succ is True:
            result.check(True, "任务成功完成: succ=True", "")
        elif succ is False:
            result.check(False, "", "任务失败: succ=False")
        else:
            result.check(False, "", f"succ字段值异常: {succ}")
        
        # 打印其他有用信息
        result.info(f"mode: {task.get('mode', 'N/A')}")
        result.info(f"retry_times: {task.get('retry_times', 'N/A')}")
        if 'bedrock_timecost' in task:
            timecost = task.get('bedrock_timecost', 0)
            result.info(f"bedrock_timecost: {timecost}ms ({timecost/1000:.1f}秒)")

def validate_database_records(config, expected_commit_id, expected_project_name, expected_task_count, platform, expected_model=None):
    """验证数据库记录的通用函数

    Args:
        config: 测试配置
        expected_commit_id: 预期的commit ID
        expected_project_name: 预期的项目名称
        expected_task_count: 预期的任务数量
        platform: 平台名称 (github/gitlab)
        expected_model: 预期的模型名称 (如 'claude4-sonnet', 'claude3.5-sonnet' 等),如果为 None 则使用默认验证
    """
    print(f"\n=== 验证{platform}平台的数据库记录 ===")

    result = ValidationResult()
    validator = DatabaseValidator(config)
    validator.expected_model = expected_model  # 传递期望的模型

    # 第一阶段：等待task分配完成（30秒）
    request_record = validator.wait_for_task_allocation(expected_commit_id)

    # 第二阶段：等待task执行完成（5分钟）
    request_record = validator.wait_for_task_completion(request_record)

    # 验证request表
    if request_record:
        validator._validate_basic_request_fields(request_record, expected_commit_id, expected_project_name, result)
        validator._validate_task_fields(request_record, expected_task_count, result)
    else:
        result.check(False, "", f"未找到commit_id为 {expected_commit_id} 的request记录")

    # 验证task表
    task_records = validator.validate_task_table(request_record, result)

    return result, request_record, task_records
