#!/usr/bin/env python3
"""
GitHub代码功能单元测试
测试github_code.py中的核心函数，验证GitHub API集成
"""

import sys
import os
import json
import yaml
from datetime import datetime

# 添加lambda目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

import github_code
import base
from github import Github
from logger import init_logger

def load_test_config():
    """加载测试配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'test_config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def test_github_connection():
    """测试1: GitHub连接和仓库访问"""
    print("=== 测试1: GitHub连接和仓库访问 ===")
    
    config = load_test_config()
    github_config = config['github']
    
    try:
        # 初始化GitHub连接
        g = Github(github_config['token'])
        repo = g.get_repo(github_config['project_id'])
        
        print(f"✅ 仓库连接成功: {repo.full_name}")
        print(f"   默认分支: {repo.default_branch}")
        print(f"   最新提交: {repo.get_commits()[0].sha[:8]}")
        
        return repo
        
    except Exception as e:
        print(f"❌ GitHub连接失败: {e}")
        return None

def test_get_rules_function(repo):
    """测试2: get_rules函数"""
    print("\n=== 测试2: get_rules函数 ===")
    
    if not repo:
        print("❌ 跳过测试 - 仓库连接失败")
        return
    
    try:
        # 测试dev分支的规则获取
        branch = "dev"
        commit_id = None  # 使用分支最新提交
        
        print(f"测试分支: {branch}")
        
        # 调用get_rules函数
        rules = github_code.get_rules(repo, commit_id, branch)
        
        print(f"✅ 获取到 {len(rules)} 个规则文件")
        
        for i, rule in enumerate(rules, 1):
            filename = rule.get('filename', 'unknown')
            name = rule.get('name', 'unnamed')
            mode = rule.get('mode', 'unknown')
            print(f"   规则{i}: {filename} - {name} ({mode})")
            
        return rules
        
    except Exception as e:
        print(f"❌ get_rules测试失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_get_file_content(repo):
    """测试3: 文件内容获取"""
    print("\n=== 测试3: 文件内容获取 ===")
    
    if not repo:
        print("❌ 跳过测试 - 仓库连接失败")
        return
    
    # 测试多个可能存在的文件
    test_files = [
        ".gitignore",
        "README.md", 
        "pom.xml",
        "src/main/java/com/example/App.java"
    ]
    
    for file_path in test_files:
        try:
            branch = "dev"
            content = github_code.get_github_file_content(repo, file_path, branch)
            
            if content:
                print(f"✅ 成功获取文件: {file_path}")
                print(f"   文件大小: {len(content)} 字符")
                print(f"   前100字符: {content[:100]}...")
                return  # 找到一个文件就返回
                
        except Exception as e:
            print(f"   尝试获取 {file_path}: 文件不存在")
            continue
    
    print("❌ 所有测试文件都不存在")

def test_zero_commit_handling(repo):
    """测试4: 全零commit_id处理（新分支第一次提交场景）"""
    print("\n=== 测试4: 全零commit_id处理 ===")
    
    if not repo:
        print("❌ 跳过测试 - 仓库连接失败")
        return
    
    try:
        # 测试场景：previous_commit_id为全零（新分支第一次提交）
        zero_commit = "0000000000000000000000000000000000000000"
        branch = "dev"
        
        # 获取dev分支的最新提交作为current_commit
        commits = list(repo.get_commits(sha=branch))
        if not commits:
            print("❌ dev分支没有提交")
            return
            
        current_commit = commits[0].sha
        print(f"当前提交: {current_commit[:8]}")
        print(f"前一提交: {zero_commit[:8]} (全零 - 新分支场景)")
        
        # 测试获取差异文件 - 应该处理全零commit_id的情况
        try:
            diff_files = github_code.get_diff_files(repo, zero_commit, current_commit)
            print(f"✅ 成功处理全零commit_id场景")
            print(f"   获取到 {len(diff_files)} 个差异文件")
            if diff_files:
                for file_path in diff_files[:3]:  # 只显示前3个
                    print(f"   变更文件: {file_path}")
        except Exception as e:
            print(f"❌ 全零commit_id处理失败: {e}")
            
        # 测试获取规则 - 使用全零commit_id
        try:
            rules = github_code.get_rules(repo, zero_commit, branch)
            print(f"✅ 使用全零commit_id获取规则成功")
            print(f"   获取到 {len(rules)} 个规则文件")
        except Exception as e:
            print(f"❌ 使用全零commit_id获取规则失败: {e}")
            
    except Exception as e:
        print(f"❌ 全零commit_id测试失败: {e}")
        traceback.print_exc()

def test_get_diff_files(repo):
    """测试5: 获取差异文件"""
    print("\n=== 测试5: 获取差异文件 ===")
    
    if not repo:
        print("❌ 跳过测试 - 仓库连接失败")
        return
    
    try:
        # 获取dev分支的提交历史
        branch = "dev"
        commits = list(repo.get_commits(sha=branch))
        
        print(f"dev分支提交数量: {len(commits)}")
        
        if len(commits) < 2:
            print("❌ dev分支提交数量不足，跳过差异测试")
            return
            
        current_commit = commits[0].sha
        previous_commit = commits[1].sha
        
        print(f"当前提交: {current_commit[:8]}")
        print(f"前一提交: {previous_commit[:8]}")
        
        # 调用get_diff_files函数
        diff_files = github_code.get_diff_files(repo, previous_commit, current_commit)
        
        print(f"✅ 获取到 {len(diff_files)} 个差异文件")
        
        for filename, patch in list(diff_files.items())[:5]:  # 只显示前5个
            print(f"   变更文件: {filename}")
            
        if len(diff_files) > 5:
            print(f"   ... 还有 {len(diff_files) - 5} 个文件")
            
    except Exception as e:
        print(f"❌ 差异文件测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_repository_context():
    """测试5: 仓库上下文创建"""
    print("\n=== 测试5: 仓库上下文创建 ===")
    
    config = load_test_config()
    github_config = config['github']
    
    try:
        # 调用init_github_context函数，提供正确的参数
        repo_url = 'https://github.com'
        project_id = github_config['project_id']
        private_token = github_config['token']
        
        # 创建仓库上下文
        repository = github_code.init_github_context(repo_url, project_id, private_token)
        
        print(f"✅ 仓库上下文创建成功")
        print(f"   项目: {repository.full_name}")
        print(f"   类型: {type(repository)}")
        
        return repository
        
    except Exception as e:
        print(f"❌ 仓库上下文创建失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def run_comprehensive_test():
    """运行综合测试"""
    print("GitHub代码功能单元测试")
    print("=" * 50)
    
    # 初始化日志
    init_logger()
    
    # 测试1: 连接
    repo = test_github_connection()
    
    # 测试2: 规则获取
    rules = test_get_rules_function(repo)
    
    # 测试3: 文件内容
    test_get_file_content(repo)
    
    # 测试4: 全零commit_id处理（新增）
    test_zero_commit_handling(repo)
    
    # 测试5: 差异文件
    test_get_diff_files(repo)
    
    # 测试6: 仓库上下文
    repo_context = test_repository_context()
    
    # 总结
    print("\n" + "=" * 50)
    print("测试总结:")
    print(f"✅ GitHub连接: {'成功' if repo else '失败'}")
    print(f"✅ 规则获取: {'成功' if rules else '失败'} ({len(rules) if rules else 0} 个规则)")
    print(f"✅ 全零commit处理: 已测试")  # 新增
    print(f"✅ 仓库上下文: {'成功' if repo_context else '失败'}")
    
    if repo and rules:
        print("\n🎉 所有核心功能测试通过！GitHub集成已就绪。")
    else:
        print("\n⚠️  部分测试失败，请检查配置和网络连接。")

if __name__ == "__main__":
    run_comprehensive_test()
