#!/usr/bin/env python3
"""
Webhook初始化脚本

设计逻辑：
1. 读取test_config.json配置文件，获取GitHub和GitLab的认证信息
2. 根据配置文件中存在的平台（github/gitlab），自动初始化对应平台的webhook
3. 删除策略：只删除URL以'/codereview'结尾的webhook，避免误删其他webhook
4. 创建策略：为每个平台创建新的webhook，监听push和merge request事件
5. 自动从配置文件读取webhook端点URL，无需手动传参

使用场景：
- 每次测试前运行此脚本，确保webhook配置正确且无重复
- 支持多平台同时配置，根据test_config.json自动判断
"""

import json
import requests
import sys
import os
from urllib.parse import urlparse

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'test_config.json')
    if not os.path.exists(config_path):
        print("❌ 错误: test_config.json 文件不存在")
        print("请先复制 test_config.json.template 并填入配置信息")
        sys.exit(1)
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ 错误: test_config.json 格式无效: {e}")
        sys.exit(1)

def validate_endpoint(endpoint):
    """验证endpoint URL是否有效"""
    if not endpoint:
        print("❌ 错误: aws.endpoint 未配置")
        print("请在 test_config.json 文件的 aws 部分添加 endpoint 字段")
        print("示例:")
        print('  "aws": {')
        print('    "endpoint": "https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod",')
        print('    ...')
        print('  }')
        return False
    
    if endpoint.startswith('your_') or endpoint.startswith('https://your-'):
        print("❌ 错误: endpoint 使用默认模板值，请填入真实的API Gateway URL")
        print("请将 test_config.json 中的 endpoint 替换为实际的API Gateway URL")
        return False
    
    try:
        parsed = urlparse(endpoint)
        if not parsed.scheme or not parsed.netloc:
            print(f"❌ 错误: endpoint URL格式无效: {endpoint}")
            print("正确格式示例: https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod")
            return False
        
        if parsed.scheme not in ['http', 'https']:
            print(f"❌ 错误: endpoint必须使用http或https协议: {endpoint}")
            return False
            
        return True
    except Exception as e:
        print(f"❌ 错误: endpoint URL解析失败: {e}")
        return False

def delete_codereview_webhooks_github(config):
    """删除GitHub中以/codereview结尾的webhooks"""
    github = config['github']
    url = f"{github['url']}/repos/{github['owner']}/{github['repo_name']}/hooks"
    headers = {
        'Authorization': f"token {github['token']}",
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        hooks = response.json()
        for hook in hooks:
            if hook['config']['url'].endswith('/codereview'):
                delete_url = f"{url}/{hook['id']}"
                delete_response = requests.delete(delete_url, headers=headers)
                if delete_response.status_code == 204:
                    print(f"已删除GitHub webhook: {hook['config']['url']}")

def create_webhook_github(config, endpoint):
    """创建GitHub webhook"""
    github = config['github']
    url = f"{github['url']}/repos/{github['owner']}/{github['repo_name']}/hooks"
    headers = {
        'Authorization': f"token {github['token']}",
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'name': 'web',
        'active': True,
        'events': ['push', 'pull_request'],
        'config': {
            'url': endpoint,
            'content_type': 'json',
            'secret': github['token']
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print(f"✅ GitHub webhook创建成功: {endpoint}")
    else:
        print(f"❌ GitHub webhook创建失败: {response.status_code}")
        print(f"响应内容: {response.text}")

def delete_codereview_webhooks_gitlab(config):
    """删除GitLab中以/codereview结尾的webhooks"""
    gitlab = config['gitlab']
    # 支持数字ID或username/repo格式
    project_id = gitlab['project_id']
    if '/' in str(project_id):
        # 如果是username/repo格式，需要URL编码
        import urllib.parse
        project_id = urllib.parse.quote(str(project_id), safe='')
    
    url = f"{gitlab['url']}/api/v4/projects/{project_id}/hooks"
    headers = {
        'Private-Token': gitlab['token']
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        hooks = response.json()
        for hook in hooks:
            if hook['url'].endswith('/codereview'):
                delete_url = f"{url}/{hook['id']}"
                delete_response = requests.delete(delete_url, headers=headers)
                if delete_response.status_code == 204:
                    print(f"已删除GitLab webhook: {hook['url']}")
    elif response.status_code == 404:
        print(f"❌ GitLab项目未找到: {project_id}")
        print("请检查 project_id 是否正确，可以是数字ID或 'username/repo' 格式")
        raise Exception(f"GitLab项目不存在: {project_id}")
    else:
        print(f"❌ 获取GitLab webhooks失败: {response.status_code}")
        print(f"响应内容: {response.text}")
        raise Exception(f"GitLab API调用失败: {response.status_code}")

def create_webhook_gitlab(config, endpoint):
    """创建GitLab webhook"""
    gitlab = config['gitlab']
    # 支持数字ID或username/repo格式
    project_id = gitlab['project_id']
    if '/' in str(project_id):
        # 如果是username/repo格式，需要URL编码
        import urllib.parse
        project_id = urllib.parse.quote(str(project_id), safe='')
    
    url = f"{gitlab['url']}/api/v4/projects/{project_id}/hooks"
    headers = {
        'Private-Token': gitlab['token'],
        'Content-Type': 'application/json'
    }
    
    payload = {
        'url': endpoint,
        'push_events': True,
        'merge_requests_events': True,
        'enable_ssl_verification': True,
        'token': gitlab['token']
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print(f"✅ GitLab webhook创建成功: {endpoint}")
    elif response.status_code == 404:
        print(f"❌ GitLab项目未找到: {gitlab['project_id']}")
        print("请检查 project_id 是否正确，可以是数字ID或 'username/repo' 格式")
        raise Exception(f"GitLab项目不存在: {gitlab['project_id']}")
    else:
        print(f"❌ GitLab webhook创建失败: {response.status_code}")
        print(f"响应内容: {response.text}")
        raise Exception(f"GitLab webhook创建失败: {response.status_code}")

def main():
    print("🚀 开始初始化Webhook...")
    
    try:
        config = load_config()
        
        # 获取并验证endpoint
        endpoint = config.get('aws', {}).get('endpoint')
        if not validate_endpoint(endpoint):
            sys.exit(1)
        
        # 确保endpoint以/codereview结尾
        if not endpoint.endswith('/codereview'):
            endpoint = endpoint.rstrip('/') + '/codereview'
        
        print(f"📡 使用webhook端点: {endpoint}")
        
        success_count = 0
        total_count = 0
        
        if 'github' in config:
            print("\n🔗 处理GitHub webhook...")
            total_count += 1
            try:
                delete_codereview_webhooks_github(config)
                create_webhook_github(config, endpoint)
                success_count += 1
            except Exception as e:
                print(f"❌ GitHub webhook处理失败: {e}")
        
        if 'gitlab' in config:
            print("\n🔗 处理GitLab webhook...")
            total_count += 1
            try:
                delete_codereview_webhooks_gitlab(config)
                create_webhook_gitlab(config, endpoint)
                success_count += 1
            except Exception as e:
                print(f"❌ GitLab webhook处理失败: {e}")
        
        print(f"\n📊 处理结果: {success_count}/{total_count} 成功")
        
        if success_count == total_count:
            print("🎉 所有webhook初始化完成！")
        else:
            print("⚠️  部分webhook初始化失败，请检查配置和网络连接。")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
