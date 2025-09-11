#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 仓库初始化脚本
用于在GitHub仓库中创建dev分支并应用仿真数据
"""

import json
import sys
import os
from pathlib import Path

# 添加当前目录到路径，以便导入同目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from simulation_lib import apply_commits_github


def load_config():
    """加载测试配置"""
    config_path = Path(__file__).parent / 'test_config.json'
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        print("请先创建 test_config.json 文件")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return json.load(f)


def main():
    """主函数"""
    print("🚀 GitHub 仓库初始化开始...")
    print("📤 Push模式: 第1次commit后push，剩余commits后再push")
    print("=" * 50)
    
    try:
        # 加载配置
        config = load_config()
        
        print("📂 开始应用所有仿真提交...")
        commit_id, project_name = apply_commits_github(config)
        
        if commit_id and project_name:
            print("\n" + "=" * 50)
            print("✅ GitHub 仓库初始化成功！")
            print(f"🔗 最终 commit ID: {commit_id}")
            print(f"🌿 dev 分支已重新创建并包含所有仿真数据")
        else:
            print("❌ GitHub 仓库初始化失败")
            
    except Exception as e:
        print(f"❌ 初始化过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
