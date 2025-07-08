import datetime
import html
import json
import logging
import os
import re

import base
import boto3
from logger import init_logger

dynamodb				= boto3.resource("dynamodb")
sns						= boto3.resource('sns')
s3						= boto3.resource("s3")

init_logger()
log = logging.getLogger('crlog_{}'.format(__name__))

def get_json_directory(project_name, commit_id):
	name = re.sub(r'[^a-zA-Z0-9]+', '_', project_name.lower())
	name = re.sub(r'^_+|_+$', '', name)
	return 'report/{}/{}'.format(name, commit_id)
	
def generate_report_content(project_name, data):

	# 读取Report Template
	path = os.path.dirname(os.path.abspath(__file__))
	json_file = os.path.join(path, 'report_template.html')
	with open(json_file, 'r') as f:
		content = f.read()

	# 准备变量
	datetime_str = datetime.datetime.now().strftime("%Y年%m月%d日 %H时%M分%S秒")
	title = f'{project_name}代码审核报告'
	subtitle = f'检测时间: {datetime_str}'

	# 替换数据
	filtered_data = [item for item in data if item.get('content') and len(item['content']) > 0]
	all_data_text = repr(base.dump_json(filtered_data, indent=4))[1:-1]
	replacement = f"""<script id="diy">
	const expand_all = false;
	const title = '{title}';
	const subtitle = '{subtitle}';
	const data = {all_data_text};
	</script>
	"""
	# print('Replacement:', dict(placement=replacement))
	content = re.sub(r'<script id="diy">.*?</script>', replacement, content, flags=re.DOTALL)
	# print('New Content:', dict(content=content))

	return title, subtitle, content

def generate_report_and_notify(record, event, context):

	commit_id = event.get('commit_id')
	request_id = event.get('request_id')
	if not commit_id: 
		raise Exception("Parameter(commit_id) in event is not provided")
	if not request_id: 
		raise Exception("Parameter(request_id) in event is not provided")
	
	try:
		result = generate_report(record, event, context)
	except Exception as ex:
		log.error(f'Fail to generate report.', extra=dict(exception=str(ex)))
		return

	# 更新数据库Task状态
	try:
		request_table = os.getenv('REQUEST_TABLE')
		dynamodb.Table(request_table).update_item(
			Key = {'commit_id': commit_id, 'request_id': request_id},
			UpdateExpression = 'set task_status = :s, report_s3key = :rs, report_url = :ru, update_time = :t',
			ExpressionAttributeValues = { 
				':s': base.STATUS_COMPLETE, 
				':rs': result.get('s3key'),
				':ru': result.get('url'),
				':t': str(datetime.datetime.now()) 
			},
			ReturnValues = 'ALL_NEW'
		)
	except Exception as ex:
		log.error('Fail to update request record report.', extra=dict(exception=str(ex)))
		return

	# 发送SNS消息
	try:
		sns_topic_arn = os.getenv('SNS_TOPIC_ARN')
		message = dict(title=result.get('title'), subtitle=result.get('subtitle'), report_url=result.get('url'), data=result.get('data'), context=context)
		response = sns.Topic(sns_topic_arn).publish(Message=base.dump_json(message), Subject=result.get('title', 'none'))
		log.info('SNS message is sent: {}'.format(response['MessageId']))
	except Exception as ex:
		log.error('Fail to send SNS message.', extra=dict(exception=str(ex)))
		return
	
def generate_report(record, event, context):

	commit_id = event.get('commit_id')
	request_id = event.get('request_id')

	label = f'request record(commit_id={commit_id}, request_id={request_id})'
	log.info(f'Generating report for {label}.')

	project_name = context.get('project_name')
	directory = get_json_directory(project_name, commit_id)
	
	# 写入data.js文件
	bucket_name = os.getenv('BUCKET_NAME')
	TASK_TABLE = os.getenv('TASK_TABLE')
	items = dynamodb.Table(TASK_TABLE).query(
		KeyConditionExpression='request_id=:rid',
		ExpressionAttributeValues={ ':rid': request_id },
		ConsistentRead=True
	)
	ret = [ item for item in items.get('Items') ]
	all_data = []
	for item in items.get('Items'):
		try:
			if item.get('succ') == True:
				request_id, number, s3_key = map(item.get, ('request_id', 'number', 'data'))
				s3_content = base.get_s3_object(s3, bucket_name, s3_key)
				json_data = json.loads(s3_content)
				log.info(f'Found successful result for task(request_id={request_id}, number={number}).', extra=dict(task={ key: str(item[key]) for key in item }, result=json_data))
				log.info(f'Parsed JSON data: {json_data}')
				if json_data:
					if type(json_data) is list:
						all_data = all_data + json_data
					else:
						all_data.append(json_data)
			else:
				log.info('Found failed result for task(request_id={request_id}, number={number}).'.format(**item), extra=dict(item=base.dump_json(item)))
		except Exception as ex:
			log.error('Fail to get result for task.', extra=dict(exception=str(ex)))
	log.info('Got all data.', extra=dict(all_data=all_data))
	
	report_data = []
	for data in all_data:
		report_data.append(dict(rule=data.get('rule'), content=data.get('content')))
	log.info('Simplify all data to report data.', extra=dict(report_data=report_data))

	# 写入HTML文件
	title, subtitle, content = generate_report_content(project_name, report_data)
	bucket_name = os.getenv('BUCKET_NAME')
	key = f'{directory}/index.html'
	base.put_s3_object(s3, bucket_name, key, content, 'Content-Type: text/html')
	log.info(f'Report is created to s3://{bucket_name}/{key}')
	
	# 为index.html产生Presign URL
	presigned_url = s3.Object(bucket_name, key).meta.client.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': key}, ExpiresIn=3600 * 24 * 5)
	log.info(f'Report URL: {presigned_url}')

	return dict(title=title, subtitle=subtitle, url=presigned_url, s3key=key, data=all_data)
