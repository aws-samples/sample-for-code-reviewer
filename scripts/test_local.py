#!/usr/bin/env python3
"""
本地快速测试脚本

这个脚本提供快速测试项目核心功能的能力,无需部署到 AWS:

1. 模型配置测试 - 验证所有模型配置正确
2. Prompt 构建测试 - 验证 prompt 生成逻辑
3. Bedrock 调用测试 - 实际调用 Bedrock API (可选)

使用方法:
  python scripts/test_local.py                    # 运行所有测试
  python scripts/test_local.py --no-bedrock       # 跳过 Bedrock API 调用
  python scripts/test_local.py --only model       # 只测试模型配置
  python scripts/test_local.py --only prompt      # 只测试 prompt 构建
  python scripts/test_local.py --only bedrock     # 只测试 Bedrock 调用
"""

import sys
import os
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def run_tests(test_files, skip_bedrock=False):
    """运行指定的测试文件"""
    import pytest

    args = ['-v', '-s']

    if skip_bedrock:
        os.environ['SKIP_BEDROCK_TESTS'] = '1'
        print("ℹ️  跳过 Bedrock API 调用测试")

    # 添加测试文件
    for test_file in test_files:
        args.append(test_file)

    print(f"\n🚀 开始运行测试...")
    print(f"   测试文件: {', '.join([os.path.basename(f) for f in test_files])}")
    print("")

    result = pytest.main(args)

    if result == 0:
        print("\n✅ 所有测试通过!")
    else:
        print(f"\n❌ 测试失败 (退出码: {result})")

    return result


def main():
    parser = argparse.ArgumentParser(
        description='本地快速测试脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/test_local.py                    # 运行所有测试
  python scripts/test_local.py --no-bedrock       # 跳过 Bedrock API 调用
  python scripts/test_local.py --only model       # 只测试模型配置
  python scripts/test_local.py --only bedrock     # 只测试 Bedrock 调用
        """
    )

    parser.add_argument('--no-bedrock', action='store_true',
                        help='跳过 Bedrock API 调用测试 (设置 SKIP_BEDROCK_TESTS=1)')

    parser.add_argument('--only', choices=['model', 'bedrock'],
                        help='只运行指定类型的测试')

    args = parser.parse_args()

    # 确定要运行的测试文件
    test_dir = os.path.join(os.path.dirname(__file__), '..', 'test', 'unit')

    test_files_map = {
        'model': os.path.join(test_dir, 'test_model_config.py'),
        'bedrock': os.path.join(test_dir, 'test_bedrock_invoke.py')
    }

    if args.only:
        test_files = [test_files_map[args.only]]
    else:
        test_files = [
            test_files_map['model'],
            test_files_map['bedrock']
        ]

    # 检查测试文件是否存在
    missing_files = [f for f in test_files if not os.path.exists(f)]
    if missing_files:
        print("❌ 以下测试文件不存在:")
        for f in missing_files:
            print(f"   - {f}")
        return 1

    # 运行测试
    return run_tests(test_files, skip_bedrock=args.no_bedrock)


if __name__ == '__main__':
    sys.exit(main())
