from logging.handlers import RotatingFileHandler
import os, json, logging, traceback
from awslambdaric.lambda_runtime_log_utils import JsonFormatter

class CustomJsonFormatter(JsonFormatter):
    def __init__(self, json_indent=None, **kwargs):
        super().__init__(**kwargs)
        self.json_indent = json_indent
        
    def format(self, record):
        log_data = json.loads(super().format(record))

        if isinstance(record.msg, dict) or isinstance(record.msg, list):
            log_data["message"] = record.msg
        else:
            log_data["message"] = record.getMessage()
        if hasattr(record, 'exception'):
            log_data['traceback'] = traceback.format_exc().split('\n')
        log_data.update({
            "path": record.pathname,
            "line": record.lineno,
        })
        if self.json_indent:
            return json.dumps(log_data, ensure_ascii=False, indent=self.json_indent)
        else:
            return json.dumps(log_data, ensure_ascii=False)

def append_stream_handler(logger):
    found = any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers)
    print('Found StreamHandler:', found)
    if not found:
        handler = logging.StreamHandler()
        formatter = CustomJsonFormatter(json_indent=2)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

def append_file_handler(logger):
    found = any(isinstance(handler, logging.FileHandler) for handler in logger.handlers)
    print('Found FileHandler:', found)
    if not found:
        handler = logging.FileHandler('log.log')
        formatter = CustomJsonFormatter(json_indent=2)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

def setup_logger(level=logging.DEBUG):
    logger = logging.getLogger()
    logger.setLevel(level)
    append_stream_handler(logger)
    return logger

def init_logger():
    aws_env = os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None
    logger = logging.getLogger()
    formatter = CustomJsonFormatter(json_indent=None if aws_env else 2)
    for handler in logger.handlers:
        handler.setFormatter(formatter)
    
    if not aws_env: 
        logger.setLevel(logging.DEBUG)
        append_stream_handler(logger)
        append_file_handler(logger)

