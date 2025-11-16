#!/usr/bin/env python3
"""
model_config.py 单元测试

测试目标: 验证模型配置管理功能
- 模型配置获取
- 模型 ID 格式化
- Extended Thinking/Reasoning 支持检测
"""

import pytest
import sys
import os

# 添加 lambda 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

from model_config import (
    get_model_config,
    get_model_id,
    supports_reasoning,
    is_claude37_or_later,
    get_all_model_names
)


class TestModelConfig:
    """model_config.py 测试类"""

    def test_get_model_config_claude35(self):
        """测试获取 Claude 3.5 Sonnet 配置"""
        config = get_model_config('claude3.5-sonnet')

        assert config is not None, "应该返回配置"
        assert config['model_id'] == 'anthropic.claude-3-5-sonnet-20240620-v1:0'
        assert config['supports_reasoning'] == False
        assert config['version'] == '3.5'

    def test_get_model_config_claude37(self):
        """测试获取 Claude 3.7 Sonnet 配置 (支持 Reasoning)"""
        config = get_model_config('claude3.7-sonnet')

        assert config is not None, "应该返回配置"
        assert config['model_id'] == 'us.anthropic.claude-3-7-sonnet-20250219-v1:0'
        assert config['supports_reasoning'] == True
        assert config['version'] == '3.7'

    def test_get_model_config_claude4(self):
        """测试获取 Claude 4 Sonnet 配置"""
        config = get_model_config('claude4-sonnet')

        assert config is not None, "应该返回配置"
        assert config['model_id'] == 'us.anthropic.claude-sonnet-4-20250514-v1:0'
        assert config['version'] == '4'

    def test_get_model_config_claude45(self):
        """测试获取 Claude 4.5 Sonnet 配置"""
        config = get_model_config('claude4.5-sonnet')

        assert config is not None, "应该返回配置"
        assert config['model_id'] == 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'
        assert config['version'] == '4.5'

    def test_get_model_config_unknown(self):
        """测试获取未知模型配置 - 应该抛出异常"""
        with pytest.raises(ValueError) as exc_info:
            get_model_config('claude-unknown')

        assert 'Unsupported model' in str(exc_info.value)

    def test_get_model_config_legacy(self):
        """测试获取旧版模型配置 (claude3-sonnet)"""
        config = get_model_config('claude3-sonnet')

        assert config is not None, "应该返回配置"
        assert config['model_id'] == 'anthropic.claude-3-sonnet-20240229-v1:0'
        assert config['supports_reasoning'] == False

    def test_get_model_id_direct(self):
        """测试直接获取模型 ID"""
        model_id = get_model_id('claude4-sonnet')
        assert model_id == 'us.anthropic.claude-sonnet-4-20250514-v1:0'

    def test_get_model_id_fallback(self):
        """测试模型 ID 获取的降级逻辑"""
        # 如果模型不在配置中,应该返回原始模型名
        model_id = get_model_id('custom-model')
        assert model_id == 'custom-model'

    def test_supports_reasoning(self):
        """测试 Reasoning 支持检测"""
        # Claude 3.5 不支持
        assert supports_reasoning('claude3.5-sonnet') == False

        # Claude 3.7 支持
        assert supports_reasoning('claude3.7-sonnet') == True

    def test_is_claude37_or_later(self):
        """测试版本检测 - >= 3.7"""
        # < 3.7
        assert is_claude37_or_later('claude3-sonnet') == False
        assert is_claude37_or_later('claude3.5-sonnet') == False

        # >= 3.7
        assert is_claude37_or_later('claude3.7-sonnet') == True
        assert is_claude37_or_later('claude4-sonnet') == True
        assert is_claude37_or_later('claude4.5-sonnet') == True

    def test_get_all_model_names(self):
        """测试获取所有模型名称"""
        models = get_all_model_names()

        assert len(models) > 0
        assert 'claude3.5-sonnet' in models
        assert 'claude3.7-sonnet' in models
        assert 'claude4-sonnet' in models
        assert 'claude4.5-sonnet' in models

        print(f"✅ 支持 {len(models)} 个模型")

    def test_model_config_for_all_models(self):
        """测试所有支持的模型配置都能正确获取"""
        models = get_all_model_names()

        for model in models:
            config = get_model_config(model)
            assert config is not None, f"模型 {model} 应该有配置"
            assert 'model_id' in config
            assert 'supports_reasoning' in config
            assert 'version' in config
            print(f"✅ {model}: model_id={config['model_id']}, reasoning={config['supports_reasoning']}")


if __name__ == '__main__':
    # 直接运行此文件时执行测试
    pytest.main([__file__, '-v', '-s'])
