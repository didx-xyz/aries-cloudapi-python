from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

cache_opts = {
    "cache.type": "memory",
    "cache.expire": 60 * 60,  # default 1 hour caching
}

cache = CacheManager(**parse_cache_config_options(cache_opts))
