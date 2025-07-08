import os, re, json, base64, decimal, datetime, traceback

str_to_float = lambda string: float(string)
str_to_int = lambda string: int(string)
is_target_file = lambda filepath, patterns: any(match_glob_pattern(filepath, pattern) for pattern in patterns)
filter_targets = lambda filepaths, targets: [path for path in filepaths if is_target_file(path, targets) ]

STATUS_COMPLETE = 'Complete'
STATUS_PROCESSING = 'Processing'
STATUS_START = 'Start'

get_s3_object = lambda s3, bucket, key: s3.Object(bucket, key).get()['Body'].read().decode('utf-8')
put_s3_object = lambda s3, bucket, key, text, content_type: s3.Object(bucket, key).put(Body=text, ContentType=content_type)

class CodelibException(Exception):
	def __init__(self, message, code=None):
		self.message = message
		self.code = code

	def __str__(self):
		return f"CodelibException: {self.message} (Code: {self.code})"

class CRError(Exception):
    def __init__(self, error_code, message):
        super().__init__(message)
        self.error_code = error_code


def trace(message):
	print('Trace>', message)

def log(message, **extra):
	caller = traceback.extract_stack()[-2]
	output = { 
		"message": message,
		"filename": os.path.basename(caller.filename),
		"line": caller.lineno,
		**extra,
		"level": "INFO", 
		"logger": "codereviewer",
		"timestamp": datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
	}
	print(dump_json(output))

def error(message, **extra):
	caller = traceback.extract_stack()[-2]
	output = { 
		"message": message,
		"filename": os.path.basename(caller.filename),
		"line": caller.lineno,
		**extra,
		"level": "ERROR", 
		"logger": "codereviewer",
		'traceback': traceback.format_exc().split('\n'),
		"timestamp": datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
	}
	print(dump_json(output))
	
class CustomJsonEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, datetime.datetime):
			return obj.strftime("%Y-%m-%d %H:%M:%S")
		if isinstance(obj, bytes):
			return str(obj, encoding='utf-8')
		if isinstance(obj, int):
			return int(obj)
		elif isinstance(obj, float):
			return float(obj)
		elif isinstance(obj, decimal.Decimal):
			return float(obj)
		# elif isinstance(obj, array):
		#    return obj.tolist()
		else:
			return super(CustomJsonEncoder, self).default(obj)
		
def dump_json(data, indent=None):
	if indent is not None:
		return json.dumps(data, cls=CustomJsonEncoder, ensure_ascii=False, indent=indent)
	else:
		return json.dumps(data, cls=CustomJsonEncoder, ensure_ascii=False)

def encode_base64(string):
	string_bytes = string.encode('utf-8')
	base64_bytes = base64.b64encode(string_bytes)
	base64_string = base64_bytes.decode('ascii')
	return base64_string

def decode_base64(base64_string):
	base64_bytes = base64_string.encode('ascii')
	string_bytes = base64.b64decode(base64_bytes)
	string = string_bytes.decode('utf-8')
	return string

def response_success_post(data, message=None):
	return response_success(data, message=message, cors_method='POST')

def response_failure_post(message, data=None):
	return response_failure(message, data=data, cors_method='POST')

def response_success_put(data, message=None):
	return response_success(data, message=message, cors_method='PUT')

def response_failure_put(message, data=None):
	return response_failure(message, data=data, cors_method='PUT')

def response_success_get(data, message=None):
	return response_success(data, message=message, cors_method='GET')

def response_failure_get(message, data=None):
	return response_failure(message, data=data, cors_method='GET')

def response_success(data, message=None, cors_method=None):
	body = dict(succ=True)
	if data is not None:
		body.update(data if isinstance(data, dict) else dict(data=data))
	ret =  { 'statusCode': 200, 'body': dump_json(body) }
	if message is not None:
		ret['message'] = message
	if cors_method:
		ret['headers'] = {
			"Access-Control-Allow-Headers" : "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,x-gitlab-token",
			"Access-Control-Allow-Origin": "*",
			"Access-Control-Allow-Methods": f"OPTIONS,{cors_method}"
		}
	return ret

def response_failure(message, data=None, cors_method=None):
	body = dict(succ=False, message=message)
	if data is not None:
		body.update(data if isinstance(data, dict) else dict(data=data))
	ret = { 'statusCode': 200, 'body': dump_json(body) }
	if cors_method:
		ret['headers'] = {
			"Access-Control-Allow-Headers" : "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,x-gitlab-token",
			"Access-Control-Allow-Origin": "*",
			"Access-Control-Allow-Methods": f"OPTIONS,{cors_method}"
		}
	return ret


def match_glob_pattern(string, pattern):
	regex = re.escape(pattern[1:] if pattern.startswith('/') else pattern)
	regex = regex.replace(r'\*\*', '.*')
	regex = regex.replace(r'\*', '[^/]*')
	regex = regex.replace(r'\?', '.')
	regex = '^' + regex + '$'
	match = re.match(regex, string)
	return bool(match)

def extract_dict(dictionary, keys_string):
	keys = re.split(r'\s*,\s*', keys_string)
	extracted_dict = [ dictionary.get(key) for key in keys ]
	return extracted_dict

def get_access_token(headers):
	if not headers: 
		return None
	return headers.get('X-Gitlab-Token') or headers.get('x-gitlab-token')
