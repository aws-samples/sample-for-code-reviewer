#!/usr/bin/env python3
"""
Mock仓库管理器
用于在测试中模拟GitLab API调用，基于文件系统中的仿真仓库数据
"""

import json
import difflib
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import Mock

try:
    from gitlab.exceptions import GitlabGetError
except ImportError:
    # 如果没有安装python-gitlab，创建一个简单的异常类
    class GitlabGetError(Exception):
        def __init__(self, message, response_code=None):
            super().__init__(message)
            self.response_code = response_code


class MockRepositoryManager:
    """Mock仓库管理器，用于模拟GitLab Project对象的行为"""
    
    def __init__(self, repository_path: str = "test/mock_data/repositories"):
        """
        初始化Mock仓库管理器
        
        Args:
            repository_path: 仓库数据存储路径
        """
        self.repository_path = Path(repository_path)
        self.repositories = {}
        self._load_repositories()
    
    def _load_repositories(self):
        """加载所有仓库的元数据"""
        for repo_dir in self.repository_path.iterdir():
            if repo_dir.is_dir():
                metadata_file = repo_dir / "repository_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        self.repositories[metadata['project_id']] = {
                            'metadata': metadata,
                            'path': repo_dir
                        }
    
    def get_mock_project(self, project_id: str) -> Mock:
        """
        获取指定项目的Mock Project对象
        
        Args:
            project_id: 项目ID
            
        Returns:
            Mock: 模拟的GitLab Project对象
        """
        if project_id not in self.repositories:
            raise ValueError(f"Repository {project_id} not found")
        
        repo_info = self.repositories[project_id]
        mock_project = Mock()
        
        # 配置各种方法的Mock行为
        mock_project.repository_compare.side_effect = lambda from_commit, to_commit: \
            self._mock_repository_compare(repo_info, from_commit, to_commit)
        
        mock_project.files.raw.side_effect = lambda file_path, ref: \
            self._mock_files_raw(repo_info, file_path, ref)
        
        mock_project.repository_tree.side_effect = lambda path="", ref="main", recursive=True: \
            self._mock_repository_tree(repo_info, path, ref, recursive)
        
        mock_project.files.get.side_effect = lambda file_path, ref: \
            self._mock_files_get(repo_info, file_path, ref)
        
        mock_project.files.create.side_effect = lambda data: \
            self._mock_files_create(repo_info, data)
        
        mock_project.branches.get.side_effect = lambda branch: \
            self._mock_branches_get(repo_info, branch)
        
        mock_project.commits.list.side_effect = lambda ref_name, all=True, order_by='created_date', sort='desc': \
            self._mock_commits_list(repo_info, ref_name, all, order_by, sort)
        
        return mock_project
    
    def _mock_repository_compare(self, repo_info: Dict, from_commit: str, to_commit: str) -> Dict:
        """模拟repository_compare方法"""
        metadata = repo_info['metadata']
        repo_path = repo_info['path']
        
        # 查找两个commit的信息
        from_commit_info = None
        to_commit_info = None
        
        for branch_name, branch_data in metadata['branches'].items():
            for commit in branch_data['commits']:
                if commit['commit_id'] == from_commit:
                    from_commit_info = commit
                if commit['commit_id'] == to_commit:
                    to_commit_info = commit
        
        if not from_commit_info or not to_commit_info:
            raise GitlabGetError("Commit not found", response_code=404)
        
        # 生成diff - 使用files和deleted_files来确定实际变更的文件
        diffs = []
        
        # 获取变更的文件
        added_or_modified_files = set(to_commit_info.get('files', []))
        deleted_files = set(to_commit_info.get('deleted_files', []))
        all_changed_files = added_or_modified_files.union(deleted_files)
        
        # 动态计算两个commit的完整文件列表
        from_all_files = set(self._calculate_all_files_at_commit(metadata, from_commit) or [])
        to_all_files = set(self._calculate_all_files_at_commit(metadata, to_commit) or [])
        
        # 处理变更的文件
        for file_path in all_changed_files:
            diff_info = {
                'new_file': file_path not in from_all_files,
                'deleted_file': file_path not in to_all_files,
                'renamed_file': False,
                'old_path': file_path,
                'new_path': file_path,
                'diff': ''
            }
            
            if not diff_info['deleted_file'] and not diff_info['new_file']:
                # 文件被修改，生成diff
                from_content = self._get_file_content(repo_path, from_commit, file_path)
                to_content = self._get_file_content(repo_path, to_commit, file_path)
                
                if from_content != to_content:
                    diff_info['diff'] = self._generate_diff(from_content, to_content, file_path)
            elif diff_info['new_file']:
                # 新文件
                to_content = self._get_file_content(repo_path, to_commit, file_path)
                if to_content is not None:
                    diff_info['diff'] = f"--- /dev/null\n+++ b/{file_path}\n" + \
                                      "\n".join(f"+{line}" for line in to_content.split('\n'))
            elif diff_info['deleted_file']:
                # 删除文件
                from_content = self._get_file_content(repo_path, from_commit, file_path)
                if from_content is not None:
                    diff_info['diff'] = f"--- a/{file_path}\n+++ /dev/null\n" + \
                                      "\n".join(f"-{line}" for line in from_content.split('\n'))
            
            if diff_info['diff']:  # 只包含有变更的文件
                diffs.append(diff_info)
        
        return {'diffs': diffs}
    
    def _mock_files_raw(self, repo_info: Dict, file_path: str, ref: str) -> bytes:
        """模拟files.raw方法"""
        repo_path = repo_info['path']
        content = self._get_file_content(repo_path, ref, file_path)
        if content is None:
            raise GitlabGetError("File not found", response_code=404)
        return content.encode('utf-8')
    
    def _mock_repository_tree(self, repo_info: Dict, path: str, ref: str, recursive: bool) -> List[Dict]:
        """模拟repository_tree方法"""
        metadata = repo_info['metadata']
        repo_path = repo_info['path']
        
        # 动态计算指定commit的完整文件列表
        commit_files = self._calculate_all_files_at_commit(metadata, ref)
        if commit_files is None:
            raise GitlabGetError("Commit not found", response_code=404)
        
        if commit_files is None:
            raise GitlabGetError("Commit not found", response_code=404)
        
        # 构建文件树
        tree_items = []
        for file_path in commit_files:
            if path and not file_path.startswith(path):
                continue
            
            # 简化处理，所有文件都标记为blob类型
            tree_items.append({
                'name': Path(file_path).name,
                'path': file_path,
                'type': 'blob',
                'id': f"blob_{hash(file_path)}",
                'mode': '100644'
            })
        
        return tree_items
    
    def _mock_files_get(self, repo_info: Dict, file_path: str, ref: str) -> Mock:
        """模拟files.get方法"""
        content = self._get_file_content(repo_info['path'], ref, file_path)
        if content is None:
            raise GitlabGetError("File not found", response_code=404)
        
        file_mock = Mock()
        file_mock.content = content.encode('utf-8')
        file_mock.save = Mock()
        return file_mock
    
    def _mock_files_create(self, repo_info: Dict, data: Dict) -> Dict:
        """模拟files.create方法"""
        # 简单返回成功响应
        return {'file_path': data['file_path'], 'branch': data['branch']}
    
    def _mock_branches_get(self, repo_info: Dict, branch: str) -> Dict:
        """模拟branches.get方法"""
        metadata = repo_info['metadata']
        
        if branch not in metadata['branches']:
            raise GitlabGetError("Branch not found", response_code=404)
        
        branch_data = metadata['branches'][branch]
        if not branch_data['commits']:
            raise GitlabGetError("No commits in branch", response_code=404)
        
        # 返回最新的commit
        latest_commit = branch_data['commits'][-1]
        return {
            'commit': {
                'id': latest_commit['commit_id']
            }
        }
    
    def _mock_commits_list(self, repo_info: Dict, ref_name: str, all: bool, order_by: str, sort: str) -> List[Dict]:
        """模拟commits.list方法"""
        metadata = repo_info['metadata']
        
        if ref_name not in metadata['branches']:
            return []
        
        branch_data = metadata['branches'][ref_name]
        commits = []
        
        for commit in branch_data['commits']:
            commits.append({
                'id': commit['commit_id'],
                'parent_ids': commit['parent_ids']
            })
        
        # 根据排序要求调整顺序
        if sort == 'desc':
            commits.reverse()
        
        return commits
    
    def _get_file_content(self, repo_path: Path, commit_id: str, file_path: str) -> Optional[str]:
        """获取指定commit中文件的内容"""
        # 查找对应的分支（简化处理，假设都在main分支）
        file_full_path = repo_path / "main" / commit_id / file_path
        
        if file_full_path.exists():
            if file_full_path.is_file():
                return file_full_path.read_text(encoding='utf-8')
            elif file_full_path.is_dir():
                # 目录不能直接读取内容，抛出异常
                raise GitlabGetError("Cannot read directory as file", response_code=400)
        return None
    
    def _generate_diff(self, from_content: str, to_content: str, file_path: str) -> str:
        """生成两个文件内容之间的diff"""
        from_lines = from_content.splitlines(keepends=True)
        to_lines = to_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            from_lines, 
            to_lines, 
            fromfile=f"a/{file_path}", 
            tofile=f"b/{file_path}",
            lineterm=''
        )
        
        return ''.join(diff)
    
    def _calculate_all_files_at_commit(self, metadata: Dict, target_commit_id: str) -> Optional[List[str]]:
        """
        动态计算指定commit时的完整文件列表
        从第一个commit开始累积计算，确保一致性
        """
        # 找到目标commit所在的分支
        target_commit = None
        commits_list = None
        
        for branch_name, branch_data in metadata['branches'].items():
            for commit in branch_data['commits']:
                if commit['commit_id'] == target_commit_id:
                    target_commit = commit
                    commits_list = branch_data['commits']
                    break
            if target_commit:
                break
        
        if not target_commit:
            return None
        
        # 从第一个commit开始累积计算文件列表
        all_files = set()
        
        for commit in commits_list:
            # 添加新增或修改的文件
            for file_path in commit.get('files', []):
                all_files.add(file_path)
            
            # 删除被删除的文件
            for file_path in commit.get('deleted_files', []):
                all_files.discard(file_path)
            
            # 如果到达目标commit，停止计算
            if commit['commit_id'] == target_commit_id:
                break
        
        return sorted(list(all_files))


# 全局实例，用于测试
mock_repo_manager = MockRepositoryManager()


def get_mock_gitlab_project(project_id: str = "123") -> Mock:
    """
    获取Mock的GitLab Project对象的便捷函数
    
    Args:
        project_id: 项目ID，默认为"123"
        
    Returns:
        Mock: 模拟的GitLab Project对象
    """
    return mock_repo_manager.get_mock_project(project_id)


if __name__ == "__main__":
    # 测试Mock仓库管理器
    project = get_mock_gitlab_project("123")
    
    # 测试获取文件内容
    try:
        content = project.files.raw(file_path="README.md", ref="d9366c45986f0717662d37887db7fd98141354c0")
        print("文件内容:", content.decode('utf-8'))
    except Exception as e:
        print("错误:", e)
    
    # 测试获取文件树
    try:
        tree = project.repository_tree(ref="b2c3d4e5f6789012345678901234567890abcdef")
        print("文件树:", [item['path'] for item in tree])
    except Exception as e:
        print("错误:", e)
    
    # 测试比较提交
    try:
        diff = project.repository_compare(
            "a1b2c3d4e5f6789012345678901234567890abcd",
            "b2c3d4e5f6789012345678901234567890abcdef"
        )
        print("差异文件数:", len(diff['diffs']))
        for d in diff['diffs']:
            print(f"  {d['new_path']}: new={d['new_file']}, deleted={d['deleted_file']}")
    except Exception as e:
        print("错误:", e)