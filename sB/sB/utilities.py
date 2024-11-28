import jwt
from datetime import datetime
from sB.middleware import LogstashLogger
import socket


def get_timeout_from_token(token):
    try:
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded_token.get("exp")

        if exp_timestamp:
            
            # Convert to seconds for cache timeout
            exp_time = datetime.fromtimestamp(exp_timestamp)
            timeout = (exp_time - datetime.now()).total_seconds()
            
            return int(timeout)
        
    except jwt.ExpiredSignatureError:
        return 0  # Token is expired, so no timeout
    except jwt.DecodeError:
        return 0  # Token could not be decoded

    return None  # In case of any other errors, return None

import json
from redis.cluster import RedisCluster as Redis
import redis

rc = Redis(host='ud-redis-node-1', port=6379)

def cache_set(key: str, value, timeout: int = None):
    # If value is a dictionary, convert it to a JSON string
    if isinstance(value, dict):
        value = json.dumps(value)
    # If value is a list, convert it to a JSON string
    elif isinstance(value, list):
        value = json.dumps(value)
    # If value is any other non-Redis compatible type, convert it to a string
    elif not isinstance(value, (str, bytes, int, float)):
        value = str(value)
    
    rc.set(key, value, timeout)

def cache_get(key: str):
    value = rc.get(key)
    if value:
        value = value.decode('utf-8')  # Decode bytes to string
        # If the value is a string and appears to be a JSON string, try to decode it
        if isinstance(value, str):
            try:
                return json.loads(value)  # Attempt to parse the JSON string back into a dictionary/list
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw string
                return value
    return value

# docker exec -it <container_id_or_name> redis-cli
# KEYS *
# GET <key>