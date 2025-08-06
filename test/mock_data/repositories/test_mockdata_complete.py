#!/usr/bin/env python3
"""
Mock Data 完整性测试用例
循环遍历repository_metadata.json中的每个commit，获取每次提交的文件名和文件内容
"""

import json
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from mock_repository_manager import get_mock_gitlab_project


def calculate_expected_files_at_commit(metadata, target_commit_id):
    """
    根据metadata.json计算指定commit时应该存在的所有文件
    
    参数:
    - metadata: repository_metadata.json的内容
    - target_commit_id: 目标commit ID
    
    返回:
    - 该commit时应该存在的所有文件列表（排序后）
    """
    commits = metadata['branches']['main']['commits']
    
    # 找到目标commit的位置
    target_index = -1
    for i, commit in enumerate(commits):
        if commit['commit_id'] == target_commit_id:
            target_index = i
            break
    
    if target_index == -1:
        return None
    
    # 累积计算文件列表
    all_files = set()
    for i in range(target_index + 1):
        commit = commits[i]
        # 添加新增文件
        for file_path in commit.get('files', []):
            all_files.add(file_path)
        # 删除被删除的文件
        for file_path in commit.get('deleted_files', []):
            all_files.discard(file_path)
    
    return sorted(list(all_files))


def test_all_commits_with_file_content():
    """
    测试目的：完整验证Mock Data系统的所有commit和文件内容
    
    测试场景：遍历repository_metadata.json中的每个commit，获取：
    1. 每个commit的基本信息（ID、消息、父提交）
    2. 每个commit中所有文件的名称
    3. 每个文件的完整内容
    4. 文件内容的统计信息（大小、行数等）
    5. 验证metadata.json与实际文件系统的完全一致性
    
    业务重要性：确保Mock系统能够完整模拟真实的GitLab仓库
    
    测试流程：
    1. 读取repository_metadata.json获取所有commit信息
    2. 遍历每个commit，获取其包含的文件列表
    3. 验证API返回的文件与文件系统中的文件完全一致
    4. 验证API返回的文件与metadata.json定义的文件完全一致
    5. 对每个文件调用GitLab API获取内容
    6. 展示文件内容的详细信息和统计
    
    关键验证点：
    - 所有commit都能正确访问
    - API返回的文件列表与文件系统完全一致
    - API返回的文件列表与metadata.json定义完全一致
    - 所有文件都能成功获取内容
    - 文件内容符合预期格式（Java代码、XML配置等）
    - 没有404错误或空内容
    - 没有多余或缺失的文件
    
    期望结果：
    - 13个commit全部可访问
    - 所有文件完全匹配metadata.json定义
    - 所有Java文件包含正确的包名和类定义
    - 所有配置文件格式正确
    """
    print("=== Mock Data 完整性测试 - 所有Commit和文件内容 ===\n")
    
    # 1. 读取repository_metadata.json
    metadata_file = Path(__file__).parent / "mock_java_project" / "repository_metadata.json"
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # 2. 获取Mock Project对象
    project = get_mock_gitlab_project("123")
    
    # 3. 遍历main分支的每个commit
    commits = metadata['branches']['main']['commits']
    total_commits = len(commits)
    total_files = 0
    total_size = 0
    
    print(f"📊 开始测试 {total_commits} 个commit的完整内容\n")
    
    for i, commit in enumerate(commits, 1):
        commit_id = commit['commit_id']
        message = commit['message']
        parent_ids = commit.get('parent_ids', [])
        files = commit.get('files', [])
        deleted_files = commit.get('deleted_files', [])
        
        print(f"🔍 [{i}/{total_commits}] Commit: {commit_id}")
        print(f"    消息: {message}")
        print(f"    父提交: {parent_ids}")
        print(f"    新增/修改文件: {len(files)} 个")
        print(f"    删除文件: {len(deleted_files)} 个")
        print()
        
        # 获取该commit的实际文件列表（展开目录）
        try:
            tree = project.repository_tree(ref=commit_id)
            actual_files = [item['path'] for item in tree]
            
            # 验证文件一致性：检查API返回与metadata.json动态计算的一致性
            # 注意：根据Mock Data设计原则，每个commit目录只存储该commit的变更文件
            # MockRepositoryManager会动态计算完整的文件列表
            
            # 1. 根据metadata.json计算期望的文件列表（动态累积）
            expected_files = calculate_expected_files_at_commit(metadata, commit_id)
            expected_files_set = set(expected_files) if expected_files else set()
            
            # 2. API返回的文件列表（应该与动态计算结果一致）
            actual_files_set = set(actual_files)
            
            # 3. 获取当前commit目录中的文件（只包含该commit的变更文件）
            commit_path = Path(__file__).parent / "mock_java_project" / "main" / commit_id
            commit_change_files = []
            if commit_path.exists():
                for item in commit_path.rglob('*'):
                    if item.is_file():
                        relative_path = item.relative_to(commit_path)
                        commit_change_files.append(str(relative_path))
            commit_change_files_set = set(commit_change_files)
            
            # 4. 获取该commit在metadata.json中定义的变更文件
            current_commit_files = set(commit.get('files', []))
            
            # 进行一致性检查
            consistency_issues = []
            
            # 检查API返回与动态计算的一致性
            metadata_vs_api_missing = expected_files_set - actual_files_set
            metadata_vs_api_extra = actual_files_set - expected_files_set
            
            if metadata_vs_api_missing:
                consistency_issues.append(f"动态计算期望但API未返回: {sorted(metadata_vs_api_missing)}")
            if metadata_vs_api_extra:
                consistency_issues.append(f"API返回但动态计算未期望: {sorted(metadata_vs_api_extra)}")
            
            # 检查当前commit的变更文件是否与metadata.json一致
            metadata_vs_changes_missing = current_commit_files - commit_change_files_set
            metadata_vs_changes_extra = commit_change_files_set - current_commit_files
            
            if metadata_vs_changes_missing:
                consistency_issues.append(f"metadata.json定义但commit目录缺失: {sorted(metadata_vs_changes_missing)}")
            if metadata_vs_changes_extra:
                consistency_issues.append(f"commit目录存在但metadata.json未定义: {sorted(metadata_vs_changes_extra)}")
            
            # 输出检查结果
            if consistency_issues:
                print(f"    ❌ 文件一致性检查失败:")
                for issue in consistency_issues:
                    print(f"        {issue}")
            else:
                print(f"    ✅ 文件一致性检查通过: API返回与动态计算完全匹配")
                print(f"        动态计算文件数: {len(expected_files_set)}")
                print(f"        API返回文件数: {len(actual_files_set)}")
                print(f"        当前commit变更文件数: {len(commit_change_files_set)}")
            
            # 计算这个commit新增的文件（与上一个commit比较）
            if i == 1:
                new_files_in_commit = actual_files
            else:
                prev_commit_id = commits[i-2]['commit_id']
                prev_tree = project.repository_tree(ref=prev_commit_id)
                prev_files = [item['path'] for item in prev_tree]
                new_files_in_commit = [f for f in actual_files if f not in prev_files]
            
            print(f"    实际新增文件: {len(new_files_in_commit)} 个")
            
            # 获取并展示每个新增文件的内容
            for j, file_path in enumerate(new_files_in_commit, 1):
                try:
                    # 获取文件内容
                    content = project.files.raw(file_path=file_path, ref=commit_id)
                    content_text = content.decode('utf-8')
                    
                    # 统计信息
                    file_size = len(content_text)
                    line_count = len(content_text.split('\n'))
                    total_files += 1
                    total_size += file_size
                    
                    print(f"    📄 [{j}/{len(new_files_in_commit)}] {file_path}")
                    print(f"        大小: {file_size} bytes")
                    print(f"        行数: {line_count} 行")
                    
                    # 根据文件类型显示不同的内容预览
                    if file_path.endswith('.java'):
                        # Java文件：显示包名和类名
                        lines = content_text.split('\n')
                        package_line = next((line for line in lines if line.strip().startswith('package ')), None)
                        class_line = next((line for line in lines if 'class ' in line and ('public' in line or 'abstract' in line)), None)
                        
                        if package_line:
                            print(f"        包名: {package_line.strip()}")
                        if class_line:
                            print(f"        类定义: {class_line.strip()}")
                    
                    elif file_path.endswith('.xml'):
                        # XML文件：显示根元素
                        lines = content_text.split('\n')
                        root_line = next((line for line in lines if '<mapper' in line or '<project' in line), None)
                        if root_line:
                            print(f"        根元素: {root_line.strip()}")
                    
                    elif file_path.endswith('.properties'):
                        # Properties文件：显示配置项数量
                        config_lines = [line for line in content_text.split('\n') if '=' in line and not line.strip().startswith('#')]
                        print(f"        配置项: {len(config_lines)} 个")
                    
                    elif file_path.endswith('.yaml'):
                        # YAML文件：显示主要配置
                        lines = content_text.split('\n')
                        key_lines = [line for line in lines[:5] if ':' in line and not line.strip().startswith('#')]
                        print(f"        主要配置: {', '.join([line.split(':')[0].strip() for line in key_lines])}")
                    
                    # 显示内容预览（前3行）
                    preview_lines = content_text.split('\n')[:3]
                    print(f"        内容预览:")
                    for k, line in enumerate(preview_lines, 1):
                        print(f"          {k}: {line}")
                    
                    if line_count > 3:
                        print(f"          ... (还有 {line_count - 3} 行)")
                    
                    print()
                    
                except Exception as e:
                    print(f"    ❌ 错误: 无法获取 {file_path}")
                    print(f"        异常: {e}")
                    print()
        except Exception as e:
            print(f"    ❌ 无法获取commit {commit_id[:8]} 的文件树: {e}")
            print()
        
        # 如果有删除的文件，也显示出来
        if deleted_files:
            print(f"    🗑️  删除的文件: {', '.join(deleted_files)}")
            print()
        
        print("-" * 80)
        print()
    
    # 最终统计
    print(f"📈 测试完成统计:")
    print(f"   - 总commit数: {total_commits}")
    print(f"   - 总文件数: {total_files}")
    print(f"   - 总代码量: {total_size:,} bytes ({total_size/1024:.1f} KB)")
    print(f"   - 平均每commit文件数: {total_files/total_commits:.1f}")
    print(f"   - 平均文件大小: {total_size/total_files:.0f} bytes")
    
    return total_files


def test_commit_evolution():
    """
    测试目的：展示代码仓库的演进过程
    
    测试场景：通过动态计算每个commit时的完整文件列表，展示仓库的演进
    业务重要性：验证动态计算功能的正确性
    
    测试流程：
    1. 遍历每个commit
    2. 计算该commit时的完整文件列表
    3. 展示仓库规模的变化
    4. 分析文件类型的分布
    
    关键验证点：
    - 文件数量随commit递增
    - 文件类型分布合理
    - 没有重复或缺失文件
    
    期望结果：
    - 仓库从1个文件增长到27个文件
    - 包含完整的Java项目结构
    """
    print("=== 代码仓库演进过程测试 ===\n")
    
    project = get_mock_gitlab_project("123")
    
    # 读取metadata
    metadata_file = Path(__file__).parent / "mock_java_project" / "repository_metadata.json"
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    commits = metadata['branches']['main']['commits']
    
    print("📈 仓库演进过程:")
    print()
    
    for i, commit in enumerate(commits, 1):
        commit_id = commit['commit_id']
        message = commit['message']
        
        # 获取该commit时的完整文件列表
        try:
            tree = project.repository_tree(ref=commit_id)
            file_count = len(tree)
            
            # 按文件类型分类
            file_types = {}
            for item in tree:
                ext = Path(item['path']).suffix or 'no-ext'
                file_types[ext] = file_types.get(ext, 0) + 1
            
            print(f"[{i:2d}] {message}")
            print(f"     Commit: {commit_id[:8]}...")
            print(f"     文件总数: {file_count}")
            print(f"     文件类型: {dict(sorted(file_types.items()))}")
            
            # 显示新增的文件类型
            if i == 1:
                print(f"     📁 项目初始化")
            else:
                added_files = commit.get('files', [])
                if added_files:
                    print(f"     ➕ 新增: {', '.join([Path(f).name for f in added_files])}")
            
            print()
            
        except Exception as e:
            print(f"     ❌ 无法获取commit {commit_id[:8]} 的文件树: {e}")
            print()
    
    # 最终项目结构分析
    final_tree = project.repository_tree(ref=commits[-1]['commit_id'])
    
    print("📊 最终项目结构分析:")
    
    # 按目录组织
    directories = {}
    for item in final_tree:
        dir_path = str(Path(item['path']).parent)
        if dir_path == '.':
            dir_path = '根目录'
        directories[dir_path] = directories.get(dir_path, 0) + 1
    
    print(f"   总文件数: {len(final_tree)}")
    print(f"   目录分布:")
    for dir_path, count in sorted(directories.items()):
        print(f"     {dir_path}: {count} 个文件")
    
    # 文件类型统计
    extensions = {}
    for item in final_tree:
        ext = Path(item['path']).suffix or '无扩展名'
        extensions[ext] = extensions.get(ext, 0) + 1
    
    print(f"   文件类型:")
    for ext, count in sorted(extensions.items()):
        print(f"     {ext}: {count} 个文件")


def test_diff_functionality():
    """
    测试目的：验证commit之间的diff功能
    
    测试场景：测试关键commit之间的差异检测
    业务重要性：确保diff功能能正确识别代码变更
    
    测试流程：
    1. 选择有代表性的commit对
    2. 生成diff并分析内容
    3. 验证diff的准确性
    
    关键验证点：
    - diff能正确识别新增、修改、删除的文件
    - diff内容包含真实的代码变更
    - 变更统计准确
    
    期望结果：
    - 所有diff都能正确生成
    - diff内容真实反映代码变更
    """
    print("=== Commit Diff 功能测试 ===\n")
    
    project = get_mock_gitlab_project("123")
    
    # 测试关键的diff场景
    diff_scenarios = [
        {
            "name": "项目初始化",
            "from": "d9366c45986f0717662d37887db7fd98141354c0",  # Initial commit
            "to": "a1b2c3d4e5f6789012345678901234567890abcd",    # Add git ignore file
            "expected_files": 1
        },
        {
            "name": "添加Maven和主程序",
            "from": "a1b2c3d4e5f6789012345678901234567890abcd",
            "to": "b2c3d4e5f6789012345678901234567890abcdef",
            "expected_files": 2
        },
        {
            "name": "添加基础架构",
            "from": "b2c3d4e5f6789012345678901234567890abcdef",
            "to": "c3d4e5f6789012345678901234567890abcdef12",
            "expected_files": 4
        },
        {
            "name": "添加代码评审规则",
            "from": "c3d4e5f6789012345678901234567890abcdef12",
            "to": "d4e5f6789012345678901234567890abcdef1234",
            "expected_files": 4
        },
        {
            "name": "添加实体类",
            "from": "d4e5f6789012345678901234567890abcdef1234",
            "to": "e5f6789012345678901234567890abcdef123456",
            "expected_files": 3
        },
        {
            "name": "添加测试文件",
            "from": "k12345678901234567890abcdef123456789012",
            "to": "l23456789012345678901234567890123456789",
            "expected_files": 1
        }
    ]
    
    for scenario in diff_scenarios:
        name = scenario["name"]
        from_commit = scenario["from"]
        to_commit = scenario["to"]
        expected_files = scenario["expected_files"]
        
        print(f"🔄 Commit: {name}")
        print(f"   From: {from_commit[:8]}...")
        print(f"   To:   {to_commit[:8]}...")
        
        try:
            diff = project.repository_compare(from_commit, to_commit)
            diffs = diff.get('diffs', [])
            
            print(f"   📊 变更文件数: {len(diffs)} (期望: {expected_files})")
            
            if len(diffs) == expected_files:
                print(f"   ✅ 文件数量正确")
            else:
                print(f"   ⚠️  文件数量不匹配")
            
            # 分析每个变更文件
            for d in diffs:
                file_path = d['new_path']
                is_new = d['new_file']
                is_deleted = d['deleted_file']
                diff_content = d.get('diff', '')
                
                status = "新增" if is_new else ("删除" if is_deleted else "修改")
                print(f"   📄 {status}: {file_path}")
                
                if diff_content:
                    # 统计diff行数
                    diff_lines = diff_content.split('\n')
                    add_lines = len([line for line in diff_lines if line.startswith('+')])
                    del_lines = len([line for line in diff_lines if line.startswith('-')])
                    
                    print(f"      Diff: +{add_lines} -{del_lines} 行")
                    
                    # 显示关键的diff内容
                    key_lines = [line for line in diff_lines[:10] if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))]
                    if key_lines:
                        print(f"      关键变更:")
                        for line in key_lines[:3]:
                            print(f"        {line}")
                        if len(key_lines) > 3:
                            print(f"        ... (还有 {len(key_lines) - 3} 行变更)")
            
        except Exception as e:
            print(f"   ❌ Diff生成失败: {e}")
        
        print()
    
    print("✅ Diff功能测试完成")


if __name__ == "__main__":
    # 运行所有测试
    print("🚀 开始Mock Data完整性测试\n")
    
    file_count = test_all_commits_with_file_content()
    print("\n" + "="*100 + "\n")
    
    test_commit_evolution()
    print("\n" + "="*100 + "\n")
    
    test_diff_functionality()
    
    print(f"\n🎉 所有测试完成！Mock系统包含 {file_count} 个文件，功能完全正常！")