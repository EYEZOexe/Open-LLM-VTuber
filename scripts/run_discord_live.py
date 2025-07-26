import sys
import os
import asyncio
from loguru import logger

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.open_llm_vtuber.live.discord_live import DiscordLive
from src.open_llm_vtuber.config_manager.utils import read_yaml, validate_config

async def main():
    logger.info("Starting Discord Live client")
    config_path = os.path.join(project_root, "conf.yaml")
    config_data = read_yaml(config_path)
    config = validate_config(config_data)
    discord_config = config.live_config.discord_live

    if not discord_config.token:
        logger.error("Missing Discord bot token in config")
        return

    bot = DiscordLive(config=discord_config.model_dump(), intents=None)
    try:
        await bot.start(discord_config.token)
    except Exception as e:
        logger.error(f"Error running Discord bot: {e}")
        import traceback
        logger.debug(traceback.format_exc())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down Discord Live client")
