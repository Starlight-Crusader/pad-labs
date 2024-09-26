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
            
            return timeout
        
    except jwt.ExpiredSignatureError:
        return 0  # Token is expired, so no timeout
    except jwt.DecodeError:
        return 0  # Token could not be decoded

    return None  # In case of any other errors, return None
