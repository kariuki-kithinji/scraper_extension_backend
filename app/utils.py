from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache

# Initialize extensions
cache = Cache()
limiter = Limiter(key_func=get_remote_address)