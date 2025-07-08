import os, datetime
import base, boto3, report

dynamodb				= boto3.resource("dynamodb")

def is_datetime_expired(datetime_text, duration):
	now_datetime = datetime.datetime.now()
	past_datetime = now_datetime - datetime.timedelta(seconds=duration)
	past_datetime_text = str(past_datetime)
	return datetime_text < past_datetime_text

def check_request_progress_by_pksk(commit_id, request_id, log):
	"""
	检查Request Record的进度状态，如果已完成（含超时），则执行后续报告流程
	@params commit_id request表的PK
	@params request_id request表的SK
	"""
	table_name = os.getenv('REQUEST_TABLE')
	item = dynamodb.Table(table_name).get_item(Key=dict(commit_id=commit_id, request_id=request_id), ConsistentRead=True)
	check_request_progress(item.get('Item'), log)


def check_request_progress(record, log):
	"""
	检查Request Record的进度状态，如果已完成（含超时），则执行后续报告流程
	@params record request表记录
	"""

	commit_id, request_id, mode, project_name, create_time, total, completes, failures = base.extract_dict(record, 'commit_id, request_id, mode, project_name, create_time, task_total, task_complete, task_failure')
	label = f'request record(commit_id={commit_id}, request_id={request_id})'
	log.info(f'Checking incomplete request record(commit_id={commit_id}, request_id={request_id})...')

	is_completed = False
	
	# 检查整个Code Review是否完成
	try:
		if completes + failures >= total:
			is_completed = True
			log.info(f'Mark code review complete. For all sub-task are complete for {label}.')
		else:
			log.info(f'Code review is uncomplete. Completes({completes}) + Failures({failures}) < Total({total}) for {label}.')
		
		# 检查整个Code Review是否超时
		timeout = base.str_to_int(os.getenv('REPORT_TIMEOUT_SECONDS', '900'))
		if type(timeout) == int:
			if is_datetime_expired(create_time, timeout):
				is_completed = True
				log.info(f'Mark code review complete. For timeout({timeout} seconds for {label}.')
		else:
			log.info(f'Error: REPORT_TIMEOUT_SECONDS({timeout}) provided is not a number.')
	except Exception as ex:
		log.error('Fail to check progress.', extra=dict(exception=str(ex)))
		is_completed = False
		
	# Code Review完成，则产生报告
	if is_completed:
		try:
			event = dict(commit_id = commit_id, request_id = request_id, mode = mode)
			context = dict(project_name=project_name)
			report.generate_report_and_notify(None, event, context)
		except Exception as ex:
			log.error('Fail to generate report and notify.', extra=dict(exception=str(ex)))
			return
		


	