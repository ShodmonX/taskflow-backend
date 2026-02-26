import json

from redis.asyncio import Redis

from app.core.config import settings


redis_client = Redis.from_url(settings.redis_url, decode_responses=True)

async def redis_set_json(key: str, value: dict, ttl_seconds: int) -> None:
    """
    Asynchronously sets a JSON-serializable dictionary value in Redis with a specified TTL.

    Args:
        key (str): The Redis key under which the value will be stored.
        value (dict): The dictionary to be serialized as JSON and stored.
        ttl_seconds (int): Time-to-live for the key in seconds.

    Returns:
        None
    """
    await redis_client.set(name=key, value=json.dumps(value), ex=ttl_seconds)

async def redis_get_json(key: str) -> dict | None:
    """
    Asynchronously retrieves a JSON-encoded value from Redis by key and returns it as a dictionary.

    Args:
        key (str): The Redis key to retrieve.

    Returns:
        dict | None: The decoded JSON object as a dictionary if the key exists, otherwise None.
    """
    raw = await redis_client.get(key)
    return json.loads(raw) if raw else None

async def redis_del(key: str) -> int:
    """
    Asynchronously deletes a key from the Redis database.

    Args:
        key (str): The key to be deleted from Redis.

    Returns:
        int: The number of keys that were removed (0 if the key does not exist, 1 if the key was deleted).

    Raises:
        Any exceptions raised by the underlying Redis client.
    """
    delete_resp = await redis_client.delete(key)
    return int(delete_resp)


async def redis_set_add(key: str, *values: str) -> int:
    if not values:
        return 0
    added = await redis_client.sadd(key, *values)
    return int(added)


async def redis_set_remove(key: str, *values: str) -> int:
    if not values:
        return 0
    removed = await redis_client.srem(key, *values)
    return int(removed)


async def redis_set_members(key: str) -> set[str]:
    members = await redis_client.smembers(key)
    return set(members)


async def redis_ttl_seconds(key: str) -> int:
    ttl = await redis_client.ttl(key)
    return int(ttl)
