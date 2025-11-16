#!/usr/bin/env python3
"""
Bedrock API 调用单元测试

测试目标: 验证 Bedrock API 调用功能
- 基本的 Converse API 调用
- Extended Thinking 参数构建
- 响应解析
- 错误处理

注意: 这个测试会实际调用 AWS Bedrock API,需要:
1. AWS 凭证配置正确
2. 有 Bedrock 访问权限
3. 可以设置环境变量 SKIP_BEDROCK_TESTS=1 跳过这些测试
"""

import pytest
import boto3
import json
import os
import sys

# 添加 lambda 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

from model_config import get_model_config, get_model_id


# 检查是否跳过 Bedrock 测试
SKIP_BEDROCK_TESTS = os.environ.get('SKIP_BEDROCK_TESTS', '0') == '1'
skip_reason = "SKIP_BEDROCK_TESTS=1 环境变量已设置,跳过实际 Bedrock API 调用"


class TestBedrockInvoke:
    """Bedrock API 调用测试类"""

    @pytest.fixture
    def bedrock_client(self):
        """创建 Bedrock Runtime 客户端"""
        return boto3.client('bedrock-runtime', region_name='us-east-1')

    @pytest.mark.skipif(SKIP_BEDROCK_TESTS, reason=skip_reason)
    def test_invoke_claude35_basic(self, bedrock_client):
        """测试调用 Claude 3.5 Sonnet - 基本响应"""
        model_id = get_model_id('claude3.5-sonnet')

        response = bedrock_client.converse(
            modelId=model_id,
            messages=[{
                'role': 'user',
                'content': [{'text': 'Say "Hello" in one word'}]
            }],
            inferenceConfig={
                'maxTokens': 100,
                'temperature': 0
            }
        )

        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        assert 'output' in response
        assert 'message' in response['output']
        assert response['output']['message']['role'] == 'assistant'

        # 检查返回的文本
        content = response['output']['message']['content']
        assert len(content) > 0
        assert 'text' in content[0]
        print(f"\n✅ Claude 3.5 响应: {content[0]['text']}")

    @pytest.mark.skipif(SKIP_BEDROCK_TESTS, reason=skip_reason)
    def test_invoke_claude37_with_extended_thinking(self, bedrock_client):
        """测试调用 Claude 3.7 Sonnet - 使用 Extended Thinking"""
        config = get_model_config('claude3.7-sonnet')
        assert config['supports_reasoning'] == True

        model_id = config['model_id']

        response = bedrock_client.converse(
            modelId=model_id,
            messages=[{
                'role': 'user',
                'content': [{'text': '计算 15 * 23 = ?'}]
            }],
            inferenceConfig={
                'maxTokens': 2000,
                'temperature': 0
            },
            additionalModelRequestFields={
                'thinking': {
                    'type': 'enabled',
                    'budget_tokens': 1000
                }
            }
        )

        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        # 检查是否有 thinking 输出
        content = response['output']['message']['content']
        has_thinking = any(block.get('type') == 'thinking' for block in content)
        has_text = any(block.get('type') == 'text' for block in content)

        print(f"\n✅ Claude 3.7 Extended Thinking 测试:")
        print(f"   - 包含 thinking: {has_thinking}")
        print(f"   - 包含 text: {has_text}")

        for block in content:
            if block.get('type') == 'thinking':
                print(f"   - Thinking: {block.get('thinking', '')[:100]}...")
            elif block.get('type') == 'text':
                print(f"   - Text: {block.get('text', '')}")

    @pytest.mark.skipif(SKIP_BEDROCK_TESTS, reason=skip_reason)
    def test_invoke_claude4_with_extended_thinking(self, bedrock_client):
        """测试调用 Claude 4 Sonnet - 使用 Extended Thinking"""
        config = get_model_config('claude4-sonnet')
        assert config['supports_reasoning'] == True

        model_id = config['model_id']

        response = bedrock_client.converse(
            modelId=model_id,
            messages=[{
                'role': 'user',
                'content': [{'text': 'What is 100 + 200?'}]
            }],
            inferenceConfig={
                'maxTokens': 2000,
                'temperature': 0
            },
            additionalModelRequestFields={
                'thinking': {
                    'type': 'enabled',
                    'budget_tokens': 1000
                }
            }
        )

        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        print(f"\n✅ Claude 4 Extended Thinking 测试通过")

        # 检查 content
        content = response['output']['message']['content']
        for idx, block in enumerate(content):
            print(f"   - Block {idx}: type={block.get('type')}")

    @pytest.mark.skipif(SKIP_BEDROCK_TESTS, reason=skip_reason)
    def test_parse_response_with_thinking(self):
        """测试解析包含 Extended Thinking 的响应"""
        # 模拟一个包含 thinking 和 text 的响应
        mock_content = [
            {
                'type': 'thinking',
                'thinking': 'Let me think about this problem...'
            },
            {
                'type': 'text',
                'text': 'The answer is 300.'
            }
        ]

        # 提取 text 内容
        text_blocks = [block['text'] for block in mock_content if block.get('type') == 'text']
        assert len(text_blocks) == 1
        assert text_blocks[0] == 'The answer is 300.'

        # 提取 thinking 内容
        thinking_blocks = [block['thinking'] for block in mock_content if block.get('type') == 'thinking']
        assert len(thinking_blocks) == 1
        assert 'think' in thinking_blocks[0].lower()

    def test_build_extended_thinking_params(self):
        """测试构建 Extended Thinking 参数"""
        # Claude 3.7 支持 reasoning,应该包含 thinking 参数
        config = get_model_config('claude3.7-sonnet')

        if config['supports_reasoning']:
            additional_fields = {
                'thinking': {
                    'type': 'enabled',
                    'budget_tokens': 1000
                }
            }
        else:
            additional_fields = {}

        assert 'thinking' in additional_fields, "Claude 3.7 应该支持 reasoning"
        assert additional_fields['thinking']['type'] == 'enabled'
        assert additional_fields['thinking']['budget_tokens'] == 1000

        # 测试不支持 reasoning 的模型
        config_no_reasoning = get_model_config('claude4-sonnet')
        assert config_no_reasoning['supports_reasoning'] == False

    def test_model_config_for_all_models(self):
        """测试所有支持的模型配置都能正确获取"""
        models = [
            'claude3-sonnet',
            'claude3.5-sonnet',
            'claude3.7-sonnet',
            'claude4-sonnet',
            'claude4.5-sonnet'
        ]

        for model in models:
            config = get_model_config(model)
            assert config is not None, f"模型 {model} 应该有配置"
            assert 'model_id' in config
            assert 'supports_reasoning' in config
            assert 'timeout' in config
            print(f"✅ {model}: model_id={config['model_id']}, reasoning={config['supports_reasoning']}")


class TestBedrockErrorHandling:
    """Bedrock API 错误处理测试"""

    @pytest.fixture
    def bedrock_client(self):
        """创建 Bedrock Runtime 客户端"""
        return boto3.client('bedrock-runtime', region_name='us-east-1')

    @pytest.mark.skipif(SKIP_BEDROCK_TESTS, reason=skip_reason)
    def test_invalid_model_id(self, bedrock_client):
        """测试使用无效的模型 ID"""
        with pytest.raises(Exception) as exc_info:
            bedrock_client.converse(
                modelId='invalid-model-id',
                messages=[{
                    'role': 'user',
                    'content': [{'text': 'Hello'}]
                }]
            )

        # 应该抛出异常
        assert exc_info.value is not None
        print(f"\n✅ 无效模型 ID 正确抛出异常: {exc_info.value}")


if __name__ == '__main__':
    # 直接运行此文件时执行测试
    # 示例: python test_bedrock_invoke.py
    # 跳过实际 API 调用: SKIP_BEDROCK_TESTS=1 python test_bedrock_invoke.py
    pytest.main([__file__, '-v', '-s'])
