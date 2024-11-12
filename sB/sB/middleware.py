import json
import requests
from datetime import datetime
import os
import socket

class LogstashLogger:
    def __init__(self):
        self.logstash_host = os.getenv('LOGSTASH_HOST', 'logstash')
        self.logstash_port = os.getenv('LOGSTASH_PORT', 6000)
        self.service_name = os.getenv('SERVICE_NAME', f'service_{os.getenv('SERVICE_TYPE').lower()}')

    def log(self, message, level='info'):
        try:
            log_data = {
                "service": self.service_name,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "level": level
            }
            
            requests.post(
                f'http://{self.logstash_host}:{self.logstash_port}',
                json=log_data,
                headers={'Content-Type': 'application/json'},
                timeout=1
            )
        except Exception:
            pass

    def info(self, message):
        self.log(message, 'info')

    def error(self, message):
        self.log(message, 'error')

    def warn(self, message):
        self.log(message, 'warn')

    def debug(self, message):
        self.log(message, 'debug')

logger = LogstashLogger()

class LogstashMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        log_info = {
            "service": f"{logger.service_name}_{socket.gethostbyname(socket.gethostname())}"
        }

        if 400 <= response.status_code < 600:
            try:
                error_detail = json.loads(response.content)['detail']
            except Exception:
                error_detail = 'Unknown error'

            log_info['msg'] = f"ERROR: Request {request.method} : {request.path} - {response.status_code} : {error_detail}"
        else:
            log_info['msg'] = f"LOG: Request {request.method} : {request.path}"

        if int(os.getenv('LOGGING')):
            logger.info(json.dumps(log_info))
            
        return response