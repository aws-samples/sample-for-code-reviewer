"""
Model Configuration Module
Centralized management for all Claude model configurations
"""

MODEL_CONFIGS = {
    # Claude 3.7 Series (uses cross-region inference)
    'claude3.7-sonnet': {
        'model_id': 'us.anthropic.claude-3-7-sonnet-20250219-v1:0',  # Cross-region inference model ID
        'supports_reasoning': True,
        'version': '3.7',
        'timeout': 900,  # 15 minutes (Lambda max)
        'param_restriction': None,
    },

    # Claude 4 Series (uses cross-region inference)
    'claude4-opus': {
        'model_id': 'us.anthropic.claude-opus-4-20250514-v1:0',  # Cross-region inference model ID
        'supports_reasoning': True,  # Supports interleaved-thinking and dev-full-thinking via anthropic_beta
        'version': '4',
        'timeout': 900,  # 15 minutes (Lambda max)
        'param_restriction': None,
    },
    'claude4-opus-4.1': {
        'model_id': 'us.anthropic.claude-opus-4-1-20250805-v1:0',  # Cross-region inference model ID
        'supports_reasoning': True,  # Supports interleaved-thinking and dev-full-thinking via anthropic_beta
        'version': '4.1',
        'timeout': 900,  # 15 minutes (Lambda max)
        'param_restriction': None,
    },
    'claude4-sonnet': {
        'model_id': 'us.anthropic.claude-sonnet-4-20250514-v1:0',  # Cross-region inference model ID
        'supports_reasoning': True,  # Supports interleaved-thinking and dev-full-thinking via anthropic_beta
        'version': '4',
        'timeout': 900,  # 15 minutes (Lambda max)
        'param_restriction': None,
    },

    # Claude 4.5 Series (uses cross-region inference, with parameter restrictions)
    'claude4.5-sonnet': {
        'model_id': 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',  # Cross-region inference model ID
        'supports_reasoning': True,  # Supports interleaved-thinking and dev-full-thinking via anthropic_beta
        'version': '4.5',
        'timeout': 900,  # 15 minutes (Lambda max)
        'param_restriction': 'temperature_only',  # Can only use temperature
    },
    'claude4.5-haiku': {
        'model_id': 'us.anthropic.claude-haiku-4-5-20251001-v1:0',  # Cross-region inference model ID
        'supports_reasoning': True,  # Supports interleaved-thinking and dev-full-thinking via anthropic_beta
        'version': '4.5',
        'timeout': 900,  # 15 minutes (Lambda max)
        'param_restriction': 'temperature_only',  # Can only use temperature
    },

    # Existing Claude 3/3.5 Models (backward compatibility)
    'claude3.5-sonnet': {
        'model_id': 'anthropic.claude-3-5-sonnet-20240620-v1:0',
        'supports_reasoning': False,
        'version': '3.5',
        'timeout': 120,
        'param_restriction': None,
    },
    'claude3-opus': {
        'model_id': 'anthropic.claude-3-opus-20240229-v1:0',
        'supports_reasoning': False,
        'version': '3',
        'timeout': 120,
        'param_restriction': None,
    },
    'claude3-sonnet': {
        'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        'supports_reasoning': False,
        'version': '3',
        'timeout': 120,
        'param_restriction': None,
    },
    'claude3-haiku': {
        'model_id': 'anthropic.claude-3-haiku-20240307-v1:0',
        'supports_reasoning': False,
        'version': '3',
        'timeout': 120,
        'param_restriction': None,
    },
    'claude3': {  # Default mapping
        'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        'supports_reasoning': False,
        'version': '3',
        'timeout': 120,
        'param_restriction': None,
    },
}


def get_model_config(model_name):
    """
    Get model configuration by model name

    Args:
        model_name: Model name (e.g., 'claude3.7-sonnet', 'claude4.5-sonnet')

    Returns:
        dict: Model configuration

    Raises:
        ValueError: If model is not supported
    """
    config = MODEL_CONFIGS.get(model_name)
    if not config:
        raise ValueError(f'Unsupported model: {model_name}')
    return config.copy()


def is_claude37_or_later(model_name):
    """
    Check if the model is Claude 3.7 or later version

    Args:
        model_name: Model name

    Returns:
        bool: True if version >= 3.7
    """
    config = get_model_config(model_name)
    version = config.get('version', '3')

    try:
        # Parse version string (e.g., "3.7" -> major=3, minor=7)
        if '.' in version:
            parts = version.split('.')
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
        else:
            major = int(version)
            minor = 0

        # Check if version >= 3.7
        return (major > 3) or (major == 3 and minor >= 7)
    except (ValueError, IndexError):
        return False


def get_all_model_names():
    """
    Get all supported model names

    Returns:
        list: List of all supported model names
    """
    return list(MODEL_CONFIGS.keys())


def supports_reasoning(model_name):
    """
    Check if the model supports reasoning capability

    Args:
        model_name: Model name

    Returns:
        bool: True if model supports reasoning
    """
    config = get_model_config(model_name)
    return config.get('supports_reasoning', False)


def get_model_id(model_name):
    """
    Get Bedrock model ID by model name

    Args:
        model_name: Model name (e.g., 'claude4-sonnet')

    Returns:
        str: Bedrock model ID, or original model_name if not found
    """
    try:
        config = get_model_config(model_name)
        return config['model_id']
    except (ValueError, KeyError):
        # Fallback: return original model name
        return model_name
