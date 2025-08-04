"""
测试环境配置

这个文件包含所有测试用例需要的环境变量配置。
在运行测试前，这些环境变量会被自动设置。
"""

import os

# 项目配置
PROJECT_NAME = 'code-reviewer-demo'
AWS_ACCOUNT_ID = '257712309840'
AWS_REGION = 'us-east-1'

def generate_test_config():
    """
    根据项目名称生成测试环境配置
    
    这样可以轻松切换不同的测试环境，只需要修改PROJECT_NAME即可
    """
    return {
        # 数据库表名 - 使用项目名称前缀
        'REQUEST_TABLE': f'{PROJECT_NAME}-request',
        'TASK_TABLE': f'{PROJECT_NAME}-task', 
        'RULE_TABLE': f'{PROJECT_NAME}-rule',
        'REPOSITORY_TABLE': f'{PROJECT_NAME}-repository',
        
        # S3存储 - 使用项目名称和账户ID
        'BUCKET_NAME': f'{PROJECT_NAME}-report-{AWS_ACCOUNT_ID}-{AWS_REGION}',
        
        # Lambda函数名 - 使用项目名称前缀
        'TASK_DISPATCHER_FUN_NAME': f'{PROJECT_NAME}-task-dispatcher',
        
        # SQS队列 - 使用项目名称和账户信息
        'TASK_SQS_URL': f'https://sqs.{AWS_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/{PROJECT_NAME}-queue',
        
        # SNS通知 - 使用项目名称和账户信息
        'SNS_TOPIC_ARN': f'arn:aws:sns:{AWS_REGION}:{AWS_ACCOUNT_ID}:{PROJECT_NAME}-topic',
        
        # SMTP邮件配置 - 测试环境使用模拟配置
        'SMTP_SERVER': 'smtp.test.com',
        'SMTP_PORT': '587',
        'SMTP_USERNAME': 'test@example.com',
        'SMTP_PASSWORD': 'test-password',
        
        # 报告配置
        'REPORT_SENDER': f'{PROJECT_NAME}@example.com',
        'REPORT_RECEIVER': f'developer-{PROJECT_NAME}@example.com',
        'REPORT_TIMEOUT_SECONDS': '900',
    }

# 生成测试环境配置
TEST_ENV_CONFIG = generate_test_config()

def setup_test_environment():
    """
    设置测试环境变量
    
    这个函数会在测试开始前被调用，设置所有必要的环境变量。
    如果环境变量已经存在，不会覆盖（允许用户自定义配置）。
    """
    for key, value in TEST_ENV_CONFIG.items():
        if key not in os.environ:
            os.environ[key] = value
            print(f"✅ 设置测试环境变量: {key} = {value}")
        else:
            print(f"ℹ️  使用现有环境变量: {key} = {os.environ[key]}")

def cleanup_test_environment():
    """
    清理测试环境变量
    
    测试完成后调用，清理设置的环境变量。
    """
    for key in TEST_ENV_CONFIG.keys():
        if key in os.environ and os.environ[key] == TEST_ENV_CONFIG[key]:
            del os.environ[key]
            print(f"🧹 清理测试环境变量: {key}")

def get_test_config(key):
    """
    获取测试配置值
    
    Args:
        key: 配置键名
        
    Returns:
        配置值，如果不存在返回None
    """
    return TEST_ENV_CONFIG.get(key)

def set_project_name(project_name, aws_account_id=None, aws_region=None):
    """
    设置项目名称并重新生成配置
    
    Args:
        project_name: 项目名称
        aws_account_id: AWS账户ID（可选）
        aws_region: AWS区域（可选）
    """
    global PROJECT_NAME, AWS_ACCOUNT_ID, AWS_REGION, TEST_ENV_CONFIG
    
    PROJECT_NAME = project_name
    if aws_account_id:
        AWS_ACCOUNT_ID = aws_account_id
    if aws_region:
        AWS_REGION = aws_region
    
    # 重新生成配置
    TEST_ENV_CONFIG = generate_test_config()
    print(f"✅ 更新项目配置: {PROJECT_NAME} (账户: {AWS_ACCOUNT_ID}, 区域: {AWS_REGION})")

def get_project_info():
    """
    获取当前项目信息
    
    Returns:
        包含项目名称、账户ID、区域的字典
    """
    return {
        'project_name': PROJECT_NAME,
        'aws_account_id': AWS_ACCOUNT_ID,
        'aws_region': AWS_REGION
    }

def print_test_config():
    """
    打印当前测试配置
    """
    print(f"\n📋 当前测试环境配置 (项目: {PROJECT_NAME}):")
    print("=" * 60)
    print(f"🏷️  项目名称: {PROJECT_NAME}")
    print(f"🏢 AWS账户: {AWS_ACCOUNT_ID}")
    print(f"🌍 AWS区域: {AWS_REGION}")
    print("-" * 60)
    for key, value in TEST_ENV_CONFIG.items():
        current_value = os.environ.get(key, '未设置')
        status = "✅" if current_value == value else "⚠️"
        print(f"{status} {key}: {current_value}")
    print("=" * 60)