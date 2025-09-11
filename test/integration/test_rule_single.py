#!/usr/bin/env python3
"""
集成测试：测试Single模式代码评审规则
测试目标：验证.codereview/code-simplification.yaml规则的single模式评审
测试过程：
1. 本地多次commit，分两次push：第1次commit后push一次，第2-4次commit后再push一次
2. 触发webhook，验证code-simplification.yaml规则生效
3. 使用validation framework验证数据库记录和任务执行
期望输出：
- Request表记录正确创建和更新
- Task表中创建对应的single模式任务
- 所有任务最终完成或在超时内完成
"""

import json
import time
import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入共享验证框架和仿真库
from validation_framework import validate_database_records
from simulation_lib import apply_commits_github, apply_commits_gitlab


def load_config():
    """加载测试配置"""
    config_path = os.path.join(os.path.dirname(__file__), '../test_config.json')
    with open(config_path, 'r') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description='集成测试：Single模式代码评审规则')
    parser.add_argument('platform', choices=['gitlab', 'github'], help='选择平台')
    args = parser.parse_args()
    
    print(f"开始测试 {args.platform} Single模式代码评审规则...")
    print("测试目标：验证.codereview/code-simplification.yaml的single模式评审")
    print("测试策略：第1次commit后push一次，第2-4次commit后再push一次")
    
    # 加载配置
    config = load_config()
    
    try:
        # 根据平台触发webhook，使用前4个commits
        if args.platform == 'gitlab':
            commit_id, project_name = apply_commits_gitlab(config, commit_count=4)
        elif args.platform == 'github':
            commit_id, project_name = apply_commits_github(config, commit_count=4)
        
        if not commit_id:
            print("❌ 无法获取commit信息，测试终止")
            return
        
        print(f"\n提交完成，commit_id: {commit_id}")
        print(f"项目名称: {project_name}")
        
        # 等待webhook触发和处理
        print("\n等待webhook触发和task dispatcher处理...")
        time.sleep(5)
        
        print("\n--- 开始验证数据库记录 ---")
        
        # 验证数据库记录
        success = validate_database_records(
            config=config,
            expected_commit_id=commit_id,
            expected_project_name=project_name,
            expected_task_count=1,  # Single模式只有1个任务
            platform=args.platform
        )
        
        if success:
            print(f"\n✅ 测试成功：{args.platform} Single模式代码评审规则验证通过")
        else:
            print(f"\n❌ 测试失败：{args.platform} Single模式代码评审规则验证失败")
            print("   请检查validation framework的详细输出")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
