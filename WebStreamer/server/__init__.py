import logging
import os
import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp_session import setup as setup_session
from aiohttp_session.redis_storage import RedisStorage
import redis.asyncio as redis

from .panel_routes import routes as panel_routes, auth_middleware
from .stream_routes import routes as stream_routes
from ..vars import Var

logger = logging.getLogger("server")

async def setup_dependencies(app):
    """
    This function runs once on startup. It establishes the Redis connection,
    sets up the session storage, and then adds our custom middleware.
    This ensures everything is initialized in the correct order.
    """
    redis_address = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    try:
        redis_pool = redis.from_url(redis_address)
        await redis_pool.ping()
        logger.info(f"Successfully connected to Redis at {redis_address}")
        app['redis'] = redis_pool
    except Exception as e:
        logger.critical(f"FATAL: Could not connect to Redis: {e}")
        exit(1)

    storage = RedisStorage(redis_pool)
    setup_session(app, storage)
    logger.info("Session storage middleware has been configured.")

    app.middlewares.append(auth_middleware)
    logger.info("Custom authentication middleware has been added.")

    async def cleanup_redis_on_shutdown(app_instance):
        logger.info("Closing Redis connection pool.")
        await app_instance['redis'].close()
        await app_instance['redis'].connection_pool.disconnect()
        
    app.on_cleanup.append(cleanup_redis_on_shutdown)


def web_server(bot):
    logger.info("Initializing Web Server...")
    
    app = web.Application()
    app['bot'] = bot
    
    aiohttp_jinja2.setup(
        app, 
        enable_async=True,
        loader=jinja2.FileSystemLoader('WebStreamer/templates')
    )
    
    app.add_routes(stream_routes)
    app.add_routes(panel_routes)
    logger.info("Added stream and panel routes")
    
    app.on_startup.append(setup_dependencies)
    
    return app
