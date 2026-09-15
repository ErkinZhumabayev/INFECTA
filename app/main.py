# Main bot application entry point

import asyncio
import logging
import sys
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandObject
from aiogram.types import ErrorEvent

from app.config import config
from app.database.database import init_db, close_db
from app.telegram.routers.main import router as main_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Called on bot startup"""
    logger.info("Bot starting up...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Get bot info
    me = await bot.get_me()
    logger.info(f"Bot @{me.username} started successfully")
    
    # Set commands menu
    await set_bot_commands(bot)


async def on_shutdown(bot: Bot):
    """Called on bot shutdown"""
    logger.info("Bot shutting down...")
    await close_db()
    await bot.session.close()
    logger.info("Bot stopped")


async def set_bot_commands(bot: Bot):
    """Set bot commands menu"""
    from aiogram.types import BotCommand
    
    commands = [
        BotCommand(command="start", description="🚀 Начать игру"),
        BotCommand(command="lab", description="🧪 Моя лаборатория"),
        BotCommand(command="help", description="❓ Помощь"),
    ]
    
    await bot.set_my_commands(commands)


def register_routers(dp: Dispatcher):
    """Register all routers"""
    dp.include_router(main_router)
    logger.info("Routers registered")


async def run_polling():
    """Run bot with polling (development mode)"""
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment!")
        logger.error("Please set BOT_TOKEN in .env file or environment variables")
        sys.exit(1)
    
    # Create dispatcher
    dp = Dispatcher()
    
    # Register routers
    register_routers(dp)
    
    # Create bot instance
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    
    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Start polling
    try:
        logger.info("Starting polling...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Polling stopped by user")
    finally:
        await bot.session.close()


async def run_webhook(webhook_url: str, webhook_port: int = 8080):
    """Run bot with webhook (production mode)"""
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment!")
        sys.exit(1)
    
    from aiohttp import web
    
    # Create dispatcher
    dp = Dispatcher()
    
    # Register routers
    register_routers(dp)
    
    # Create bot instance
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    
    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Setup webhook
    await bot.set_webhook(url=webhook_url)
    
    # Create web server
    app = web.Application()
    app.router.add_post(f"/webhook/{config.BOT_TOKEN}", lambda request: handle_webhook(request, dp, bot))
    
    # Run server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", webhook_port)
    await site.start()
    
    logger.info(f"Webhook server started on port {webhook_port}")
    
    # Keep running
    while True:
        await asyncio.sleep(3600)


async def handle_webhook(request, dp, bot):
    """Handle webhook requests"""
    update_data = await request.json()
    update = Update(**update_data)
    await dp.feed_update(bot, update)
    return web.Response(status=200)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Virolabs Telegram Bot")
    parser.add_argument(
        "--mode",
        choices=["polling", "webhook"],
        default="polling",
        help="Run mode: polling (dev) or webhook (prod)"
    )
    parser.add_argument(
        "--webhook-url",
        type=str,
        default="",
        help="Webhook URL for production mode"
    )
    parser.add_argument(
        "--webhook-port",
        type=int,
        default=8080,
        help="Webhook server port"
    )
    
    args = parser.parse_args()
    
    if args.mode == "polling":
        asyncio.run(run_polling())
    elif args.mode == "webhook":
        if not args.webhook_url:
            logger.error("Webhook URL is required for webhook mode")
            sys.exit(1)
        asyncio.run(run_webhook(args.webhook_url, args.webhook_port))


if __name__ == "__main__":
    main()
