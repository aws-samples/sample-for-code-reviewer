import traceback
import json, os, logging
import boto3
from logger import init_logger

RULE_TABLE 				= os.getenv('RULE_TABLE')
REPOSITORY_TABLE		= os.getenv('REPOSITORY_TABLE')
	
dynamodb = boto3.resource('dynamodb')

init_logger()
log = logging.getLogger('crlog_{}'.format(__name__))

def process_repo_configs():

	# 读取Repo配置
	try:
		path = os.path.dirname(os.path.abspath(__file__))
		json_file = os.path.join(path, 'repos.json')
		with open(json_file, 'r') as f:
			repos = json.load(f)
		print('Parsed repo config list: ', repos)
	except Exception as ex:
		raise Exception(f'Fail to parse repo configs: {ex}') from ex
	
	for repo in repos:
		try:

			# 校验
			errors = []
			if not repo.get('repository_url'):
				errors.append(dict(field='repository_url', message='Field is not provided'))
			if not repo.get('branch_regexp'):
				errors.append(dict(field='branch_regexp', message='Field is not provided'))

			if not errors:
				dynamodb.Table(REPOSITORY_TABLE).put_item(Item=repo)
				print(f'Succeed to initilize repository: {repo}')
			else:
				# 输出错误信息
				print('SKIP REPOSITORY - fail to initilize repository for invalid field:', repo)
				for error in errors:
					print('Field({field}) invalid: {message}'.format(**error))
				
		except Exception as ex:
			print('SKIP REPOSITORY - fail to initilize repository for exception:', repo)
			print('Exception: ', ex)
			traceback.print_exc()
	
 
def process_rules():

	# 读取Rules
	try:
		path = os.path.dirname(os.path.abspath(__file__))
		json_file = os.path.join(path, 'rules.json')
		with open(json_file, 'r') as f:
			rules = json.load(f)
		print('Parsed rule list: ', rules)
	except Exception as ex:
		raise Exception(f'Fail to parse rules: {ex}') from ex
	
	for rule in rules:
		try:

			# 校验
			errors = []
			if rule.get('mode') not in [ 'all', 'single' ]:
				errors.append(dict(
					field='mode', 
					message='Value({}) is invalid, only "all" and "single" are valid.'.format(rule.get('mode')))
				)
			if not rule.get('model'):
				errors.append(dict(field='model', message='Field is not provided'))
			if not rule.get('number'):
				errors.append(dict(field='number', message='Field is not provided'))
			if not rule.get('name'):
				errors.append(dict(field='name', message='Field is not provided'))
			if rule.get('mode') == 'claude3':
				if not rule.get('prompt_user'):
					errors.append(dict(field='prompt_user', message='Field is not provided for model CLAUDE3'))

			if not errors:
				dynamodb.Table(RULE_TABLE).put_item(Item=rule)
				print(f'Succeed to initilize rule: {rule}')
			else:
				# 输出错误信息
				print('SKIP RULE - fail to initilize rule for invalid field:', rule)
				for error in errors:
					print('Field({field}) invalid: {message}'.format(**error))
				
		except Exception as ex:
			print('Exception: ', ex)
			traceback.print_exc()
	

def lambda_handler(event, context):
	
	log.info(event, extra=dict(label='event'))

	process_repo_configs()

	process_rules()
	
	return True
