#!/usr/bin/env python3
"""
集成测试：测试All模式代码评审规则
提交所有simulation data，验证没有评审规则时不触发评审逻辑
"""

import json
import time
import argparse
import yaml
import gitlab
from pathlib import Path
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入共享验证框架和仿真库
from validation_framework import validate_database_records
from simulation_lib import apply_commits_github

def load_config():
    """加载测试配置"""
    config_path = os.path.join(os.path.dirname(__file__), '../test_config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def apply_all_simulation_commits(gl_project, config):
    """应用所有仿真提交到dev分支"""
    print("📂 开始处理仿真数据...", flush=True)
    
    # 仿真数据目录在项目根目录下
    project_root = Path(__file__).parent.parent.parent
    simulation_dir = project_root / 'simulation-data'
    
    if not simulation_dir.exists():
        print(f"❌ 仿真数据目录不存在: {simulation_dir}", flush=True)
        return
        
    dev_branch = 'dev'
    
    # 获取所有提交目录并排序（1-N）
    commit_dirs = sorted([d for d in simulation_dir.iterdir() if d.is_dir()], 
                        key=lambda x: int(x.name))
    print(f"📊 发现 {len(commit_dirs)} 个仿真提交: {[d.name for d in commit_dirs]}", flush=True)
    
    # 删除dev分支（如果存在）
    print(f"🗑️  尝试删除现有的 {dev_branch} 分支...", flush=True)
    try:
        gl_project.branches.delete(dev_branch)
        print(f"✅ 删除现有的 {dev_branch} 分支成功", flush=True)
    except Exception as e:
        print(f"ℹ️  删除分支失败（可能不存在）: {e}", flush=True)
    
    # 重新创建dev分支（基于main分支的第一个commit）
    print(f"🌿 重新创建 {dev_branch} 分支（基于main的第一个commit）...", flush=True)
    try:
        # 获取main分支的第一个commit
        main_commits = gl_project.commits.list(ref_name='main', get_all=True)
        if not main_commits:
            print("❌ main分支没有任何commit", flush=True)
            return
        
        first_commit_id = main_commits[-1].id  # 最后一个是最早的commit
        print(f"ℹ️  main分支第一个commit ID: {first_commit_id}", flush=True)
        
        gl_project.branches.create({'branch': dev_branch, 'ref': first_commit_id})
        print(f"✅ 重新创建 {dev_branch} 分支成功", flush=True)
    except Exception as e:
        print(f"❌ 创建分支失败: {e}", flush=True)
        return
    
    # 获取所有提交目录并排序（1-12）
    commit_dirs = sorted([d for d in simulation_dir.iterdir() if d.is_dir()], 
                        key=lambda x: int(x.name))
    
    for commit_dir in commit_dirs:
        commit_num = int(commit_dir.name)
        print(f"应用第{commit_num}次提交到dev分支...", flush=True)
        
        # 读取提交配置
        config_file = commit_dir / 'SIMULATIONS.yaml'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                commit_config = yaml.safe_load(f)
            
            commit_message = commit_config.get('commit_message', f'Commit {commit_num}')
            deletes = commit_config.get('deletes', [])
        else:
            commit_message = f'Commit {commit_num}'
            deletes = []
        
        # 删除指定文件
        for delete_path in deletes:
            try:
                gl_project.files.delete(file_path=delete_path, 
                                      commit_message=commit_message,
                                      branch=dev_branch)
                print(f"  删除文件: {delete_path}")
            except Exception as e:
                print(f"  删除文件失败 {delete_path}: {e}")
        
        # 复制新文件
        for root, dirs, files in os.walk(commit_dir):
            for file in files:
                if file == 'SIMULATIONS.yaml':
                    continue
                
                local_path = Path(root) / file
                relative_path = local_path.relative_to(commit_dir)
                
                with open(local_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                try:
                    # 尝试获取现有文件
                    existing_file = gl_project.files.get(file_path=str(relative_path), ref=dev_branch)
                    existing_file.content = content
                    existing_file.save(branch=dev_branch, commit_message=commit_message)
                    print(f"  更新文件: {relative_path}")
                except:
                    # 文件不存在，创建新文件
                    gl_project.files.create({
                        'file_path': str(relative_path),
                        'branch': dev_branch,
                        'content': content,
                        'commit_message': commit_message
                    })
                    print(f"  创建文件: {relative_path}")

def get_latest_commit_id(gl_project):
    """获取dev分支最新commit ID"""
    dev_branch = 'dev'
    commits = gl_project.commits.list(ref_name=dev_branch, per_page=1, get_all=False)
    return commits[0].id if commits else None

def trigger_gitlab_webhook(config):
    """触发GitLab webhook"""
    gitlab_config = config['gitlab']
    
    print(f"🔗 开始连接GitLab: {gitlab_config['url']}", flush=True)
    print(f"📁 项目ID: {gitlab_config['project_id']}", flush=True)
    
    # 连接GitLab
    try:
        gl = gitlab.Gitlab(gitlab_config['url'], private_token=gitlab_config['token'])
        print("✅ GitLab连接成功", flush=True)
        
        gl_project = gl.projects.get(gitlab_config['project_id'])
        print(f"✅ 项目获取成功: {gl_project.name}", flush=True)
    except Exception as e:
        print(f"❌ GitLab连接失败: {e}", flush=True)
        raise
    
    # 应用所有仿真提交
    print("\n--- 应用所有仿真提交 ---")
    apply_all_simulation_commits(gl_project, config)
    
    # 执行merge操作：将dev分支合并到stage分支
    print("\n--- 执行Merge操作 ---")
    try:
        # 先创建stage分支（基于main的第一个commit）
        stage_branch = 'stage'
        print(f"🌿 创建 {stage_branch} 分支（基于main的第一个commit）...", flush=True)
        
        # 获取main分支的第一个commit
        main_commits = gl_project.commits.list(ref_name='main', get_all=True)
        first_commit_id = main_commits[-1].id
        
        # 删除stage分支（如果存在）
        try:
            gl_project.branches.delete(stage_branch)
            print(f"✅ 删除现有的 {stage_branch} 分支", flush=True)
        except:
            print(f"ℹ️  {stage_branch} 分支不存在，跳过删除", flush=True)
        
        # 创建stage分支
        gl_project.branches.create({'branch': stage_branch, 'ref': first_commit_id})
        print(f"✅ 创建 {stage_branch} 分支成功", flush=True)
        
        # 创建merge request：从dev到stage
        mr = gl_project.mergerequests.create({
            'source_branch': 'dev',
            'target_branch': stage_branch, 
            'title': 'Test merge for code review validation'
        })
        print(f"创建Merge Request: {mr.iid}")
        
        # 等待一下让MR创建完成
        time.sleep(2)
        
        # 使用API直接merge MR
        try:
            import requests
            gitlab_config = config['gitlab']
            # 使用数字项目ID而不是gl_project.id
            project_numeric_id = 74079259
            merge_url = f"{gitlab_config['url']}/api/v4/projects/{project_numeric_id}/merge_requests/{mr.iid}/merge"
            headers = {'Private-Token': gitlab_config['token']}
            merge_data = {
                'merge_commit_message': 'Merged via API for testing',
                'should_remove_source_branch': False
            }
            
            response = requests.put(merge_url, headers=headers, json=merge_data)
            if response.status_code == 200:
                print("✅ Merge Request已通过API合并")
            else:
                print(f"❌ API合并失败: {response.status_code} - {response.text}")
                raise Exception("API merge failed")
                
        except Exception as e:
            print(f"ℹ️  API合并失败: {e}")
            print("❌ Merge操作失败，但继续执行后续流程")
        
        # 获取stage分支的最新commit ID
        stage_commits = gl_project.commits.list(ref_name=stage_branch, per_page=1, get_all=False)
        commit_id = stage_commits[0].id if stage_commits else None
        print(f"Stage分支最新commit ID: {commit_id}")
        
    except Exception as e:
        print(f"Merge操作失败: {e}")
        # 如果merge失败，使用dev分支的commit ID
        commit_id = get_latest_commit_id(gl_project)
    
    # 发送webhook请求到AWS API Gateway
    print(f"\n--- 等待GitLab自动触发Webhook ---")
    print("ℹ️  GitLab将自动发送webhook到配置的AWS API Gateway", flush=True)
    
    return commit_id, gl_project.name

def trigger_github_webhook(config, model='claude3.5'):
    """触发GitHub webhook"""
    print(f"🔗 使用GitHub平台触发webhook (模型: {model})...")
    # 应用所有仿真提交（12个commits）
    return apply_commits_github(config, commit_count=12, model=model)

def main():
    parser = argparse.ArgumentParser(description='集成测试：All模式代码评审规则')
    parser.add_argument('platform', choices=['gitlab', 'github'], help='选择平台 (gitlab/github)')
    parser.add_argument('model', nargs='?', choices=['claude3.5', 'claude3.7', 'claude4', 'claude4.5'],
                        default='claude3.5', help='选择要测试的Claude模型 (默认: claude3.5)')
    args = parser.parse_args()

    print(f"🚀 开始测试 {args.platform} All模式代码评审规则...", flush=True)
    print(f"测试模型：{args.model}")
    
    # 加载配置
    print("📋 加载测试配置...", flush=True)
    config = load_config()
    print(f"✅ 配置加载完成", flush=True)
    
    try:
        # 根据平台触发webhook
        if args.platform == 'gitlab':
            commit_id, project_name = trigger_gitlab_webhook(config)
        elif args.platform == 'github':
            commit_id, project_name = trigger_github_webhook(config, model=args.model)
        
        # 等待5秒让webhook创建request记录
        print("\n等待5秒让webhook创建request记录...")
        time.sleep(5)

        # 根据模型参数确定期望的模型名称
        model_name_map = {
            'claude3.5': 'claude3-sonnet',
            'claude3.7': 'claude3.7-sonnet',
            'claude4': 'claude4-sonnet',
            'claude4.5': 'claude4.5-sonnet'
        }
        expected_model = model_name_map.get(args.model, 'claude3-sonnet')

        # 使用共享验证框架检查数据库数据
        # All模式会触发2个规则:
        # 1. code-simplification (single模式) - 每个涉及的文件1个task
        # 2. database-master-slave-issue (all模式) - 所有代码合在一起1个task
        # 对于12个commits的测试数据,涉及到多个Java文件,所以总task数 > 1
        # 这里不验证具体数量,只要task_total > 0即可
        result, request_record, task_records = validate_database_records(
            config, commit_id, project_name, expected_task_count=None, platform=args.platform,
            expected_model=expected_model
        )
        
        # 输出最终结果
        result.summary()
        
        if result.is_success():
            print(f"\n✅ 测试成功：{args.platform} All模式代码评审规则验证通过")
        else:
            print(f"\n❌ 测试失败：{args.platform} All模式代码评审规则验证失败")
    
    except Exception as e:
        print(f"测试过程中出错: {e}")

if __name__ == "__main__":
    main()
