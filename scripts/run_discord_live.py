import asyncio
import sys
import os
from loguru import logger

# Ensure modules from the src directory can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.open_llm_vtuber.live.discord_live import DiscordLive
from src.open_llm_vtuber.config_manager.utils import read_yaml, validate_config

async def main():
    logger.info("Starting Discord Live client")
    try:
        config_path = os.path.join(project_root, "conf.yaml")
        config_data = read_yaml(config_path)
        config = validate_config(config_data)
        discord_config = config.live_config.discord_live

        if not discord_config.token:
            logger.error("Missing required configuration for Discord (token)")
            return

        logger.info(f"Attempting to connect to Discord as bot user.")
        platform = DiscordLive(
            token=discord_config.token,
            character_name=discord_config.character_name,
            handle_platform_event=None  # Will be set by DiscordLive internally
        )
        await platform.run()

    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.error("Did you install discord.py? pip install discord.py")
    except Exception as e:
        logger.error(f"Error starting Discord Live client: {e}")
        import traceback
        logger.debug(traceback.format_exc())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down Discord Live client")
