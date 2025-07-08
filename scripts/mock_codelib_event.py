import json, requests

url = 'api-gateway-endpoint'
api_key_value = 'api-key-value'
commit_id = ''
access_token = ''
web_url = ''
path_with_namespace = ''

headers = { 
	'X-API-KEY': api_key_value,
	'X-Gitlab-Token': access_token
}
data = {
	'object_kind': 'push',
	'before': commit_id,
	'after': commit_id,
	'user_username': 'mock',
	'project': {
		# 'id': project_id,
		'name': 'Test Project',
		'web_url': web_url,
		'path_with_namespace': path_with_namespace,
	}
}

response = requests.post(url, data=json.dumps(data), headers=headers)
print('Response: ', response.status_code, response.text)