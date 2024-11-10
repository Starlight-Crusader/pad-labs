import jwt
from datetime import datetime, timedelta
from django.conf import settings


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

import os
import hashlib
import redis
import json

# Initialize Redis clients
redis_cluster = [
    redis.Redis(host=os.getenv('UD_CACHE_HOST_1'), port=6379),
    redis.Redis(host=os.getenv('UD_CACHE_HOST_2'), port=6379),
    redis.Redis(host=os.getenv('UD_CACHE_HOST_3'), port=6379)
]

def get_cache_instance(key: str) -> redis.Redis:
    """Determine the Redis instance for a given key using consistent hashing."""
    hash_value = int(hashlib.sha256(key.encode()).hexdigest(), 16)
    index = hash_value % len(redis_cluster)
    return redis_cluster[index]

def cache_set(key: str, value, timeout: int = None) -> None:
    """Set a key-value pair in the appropriate Redis instance."""
    redis_instance = get_cache_instance(key)
    
    # If value is a dictionary, convert it to a JSON string
    if isinstance(value, dict):
        value = json.dumps(value)
    
    # Set the value in Redis with an optional timeout
    redis_instance.set(key, value, ex=timeout)

def cache_get(key: str):
    """Retrieve a value by key from the appropriate Redis instance. Returns None if not found."""
    redis_instance = get_cache_instance(key)
    value = redis_instance.get(key)
    
    if value:
        # Attempt to decode and return the value as a dict if it was a JSON string
        try:
            return json.loads(value.decode())  # Deserialize JSON string into a dictionary
        except json.JSONDecodeError:
            return value.decode()  # Return the value as a string if it's not JSON
    return None

# docker exec -it <container_id_or_name> redis-cli
# KEYS *
# GET <key>