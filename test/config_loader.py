import json
import os

def load_test_config():
    config_path = os.path.join(os.path.dirname(__file__), 'test_config.json')
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Test config not found: {config_path}. Copy test_config.json.template and fill in your credentials.")
    
    with open(config_path, 'r') as f:
        return json.load(f)

def get_github_config():
    return load_test_config()['github']

def get_gitlab_config():
    return load_test_config()['gitlab']
