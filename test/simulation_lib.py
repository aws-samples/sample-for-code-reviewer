#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import shutil
import yaml
import git
import gitlab
from pathlib import Path
from github import Github

def get_commit_directories():
    """获取所有commit目录，按数字排序"""
    # 从test目录向上找到项目根目录，然后找simulation-data
    test_dir = Path(__file__).parent
    project_root = test_dir.parent
    commit_base = project_root / "simulation-data"
    
    if not commit_base.exists():
        return []
    
    commit_dirs = []
    for item in commit_base.iterdir():
        if item.is_dir() and item.name.isdigit():
            commit_dirs.append(item)
    
    # 按数字排序
    commit_dirs.sort(key=lambda x: int(x.name))
    return commit_dirs

def apply_commits_gitlab(config, commit_count=None, model='claude3.5'):
    """GitLab版本：所有commits完成后进行一次push"""
    return _apply_commits_impl(config, commit_count, 'gitlab', model)

def apply_commits_github(config, commit_count=None, model='claude3.5'):
    """GitHub版本：所有commits完成后进行一次push"""
    return _apply_commits_impl(config, commit_count, 'github', model)

def _apply_commits_impl(config, commit_count, platform, model):
    """统一的commit实现：所有commits完成后进行一次push"""
    platform_config = config[platform]
    
    # 获取commit目录
    commit_dirs = get_commit_directories()
    if not commit_dirs:
        print("❌ 没有找到commit目录")
        return None, None
    
    # 限制commit数量
    if commit_count:
        commit_dirs = commit_dirs[:commit_count]
    
    # 删除远程dev分支
    print(f"🔗 连接{platform.upper()} API删除远程dev分支...")
    try:
        if platform == 'gitlab':
            gl = gitlab.Gitlab(platform_config['url'], private_token=platform_config['token'])
            project = gl.projects.get(platform_config['project_id'])
            project.branches.delete('dev')
        else:  # github
            # 使用PyGithub删除分支
            g = Github(platform_config['token'])
            repo = g.get_repo(platform_config['project_id'])
            try:
                ref = repo.get_git_ref('heads/dev')
                ref.delete()
            except Exception:
                pass  # 分支不存在，忽略
        print(f"✅ 通过{platform.upper()} API删除远程 dev 分支成功")
    except Exception as e:
        print(f"ℹ️  远程dev分支不存在或删除失败: {e}")
    
    print(f"📊 准备应用前{len(commit_dirs)}个提交: {[d.name for d in commit_dirs]}")
    
    # 克隆仓库到临时目录
    print(f"🔄 克隆{platform.upper()}仓库到临时目录...")
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir) / "repo"
        
        try:
            # 构建克隆URL
            if platform == 'gitlab':
                clone_url = f"https://oauth2:{platform_config['token']}@gitlab.com/{platform_config['project_id']}.git"
            else:  # github
                clone_url = f"https://{platform_config['token']}@github.com/{platform_config['project_id']}.git"
            
            repo = git.Repo.clone_from(clone_url, repo_path)
            print("✅ 克隆成功")
        except Exception as e:
            print(f"❌ 克隆失败: {e}")
            return None, None
        
        # 切换到main分支
        repo.git.checkout('main')
        print("✅ 切换到main分支")
        
        # 删除本地dev分支（如果存在）
        try:
            repo.git.branch('-D', 'dev')
            print("✅ 删除本地 dev 分支")
        except:
            print("ℹ️  本地 dev 分支不存在，跳过删除")
        
        # 重新创建dev分支（基于main的第一个commit）
        print("🌿 重新创建 dev 分支（基于main的第一个commit）...")
        main_commits = list(repo.iter_commits('main'))
        if main_commits:
            first_commit = main_commits[-1]  # 最早的commit
            print(f"ℹ️  main分支第一个commit ID: {first_commit.hexsha[:8]}")
            repo.git.checkout('-b', 'dev', first_commit.hexsha)
            print("✅ 重新创建 dev 分支成功")
        else:
            print("❌ main分支没有commit")
            return None, None
        
        # 应用提交
        successful_commits = 0
        for i, commit_dir in enumerate(commit_dirs, 1):
            print(f"📝 应用第{i}次提交...")
            
            # 读取提交配置
            config_file = commit_dir / 'SIMULATIONS.yaml'
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    commit_config = yaml.safe_load(f)
                commit_message = commit_config.get('commit_message', f'Commit {i}')
                deletes = commit_config.get('deletes', [])
            else:
                commit_message = f'Commit {i}'
                deletes = []
            
            # 删除指定文件
            for delete_path in deletes:
                file_path = repo_path / delete_path
                if file_path.exists():
                    file_path.unlink()
                    print(f"  删除文件: {delete_path}")
            
            # 复制新文件
            for root, dirs, files in os.walk(commit_dir):
                for file in files:
                    if file == 'SIMULATIONS.yaml':
                        continue

                    local_path = Path(root) / file
                    relative_path = local_path.relative_to(commit_dir)

                    # 如果是 .codereview 目录中的 .yaml 文件，进行模型过滤
                    if '.codereview' in str(relative_path) and file.endswith('.yaml'):
                        # 检查文件名是否匹配模型
                        # 文件命名规则: <rule-name>-<model>.yaml
                        # 例如: code-simplification-claude3.5.yaml
                        if f'-{model}.yaml' not in file:
                            print(f"  跳过文件 (不匹配模型 {model}): {relative_path}")
                            continue

                    target_path = repo_path / relative_path

                    # 确保目标目录存在
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # 复制文件
                    shutil.copy2(local_path, target_path)
                    print(f"  添加文件: {relative_path}")
            
            # Git add 和 commit
            repo.git.add(".")
            # 检查是否有变更
            if repo.is_dirty():
                repo.git.commit("-m", commit_message)
                print(f"  ✅ 本地commit完成: {commit_message}")
                successful_commits += 1
            else:
                print(f"  ⚠️  没有变更需要提交，跳过commit: {commit_message}")
                continue
        
        # 所有commit完成后进行push
        if successful_commits > 0:
            print(f"📤 准备push所有{successful_commits}个成功commit...")
            commits = list(repo.iter_commits('dev', max_count=successful_commits))
            if commits:
                current_commit = repo.head.commit
                print(f"   Current commit:  {current_commit.hexsha[:8]}")
                
                # 获取项目名称
                if platform == 'gitlab':
                    project_name = project.name
                else:  # github
                    project_name = platform_config['project_id'].split('/')[-1]
                print(f"   Project name:    {project_name}")
                
                repo.git.push('origin', 'dev')
                print("✅ Push完成！")
        
        # 获取最终的commit信息
        final_commit = repo.head.commit
        commit_id = final_commit.hexsha
        
        # 获取项目名称
        if platform == 'gitlab':
            project_name = project.name
        else:  # github
            project_name = platform_config['project_id'].split('/')[-1]
        
        print(f"\n提交完成，commit_id: {commit_id}")
        print(f"项目名称: {project_name}")
        
        return commit_id, project_name
