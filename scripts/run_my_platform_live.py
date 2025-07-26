import asyncio
import sys
import os
from loguru import logger

# Ensure modules from the src directory can be imported VERY IMPORTANT TEST
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Import your platform implementation class
from src.open_llm_vtuber.live.my_platform_live import TwitchLive
from src.open_llm_vtuber.config_manager.utils import read_yaml, validate_config

async def main():
    logger.info("Starting Twitch Live client")
    while True:
        try:
            config_path = os.path.join(project_root, "conf.yaml")
            config_data = read_yaml(config_path)
            config = validate_config(config_data)
            twitch_config = config.live_config.twitch_live

            if not twitch_config.channel or not twitch_config.token:
                logger.error("Missing required configuration for Twitch (channel or token)")
                return

            logger.info(f"Attempting to connect to Twitch channel: {twitch_config.channel}")
            platform = TwitchLive(config=twitch_config.model_dump())
            await platform.run()
        except ImportError as e:
            logger.error(f"Failed to import required modules: {e}")
            logger.error("Did you install twitchio? pip install twitchio")
            break
        except Exception as e:
            logger.error(f"Error starting Twitch Live client: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            logger.info("Restarting Twitch Live client in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down Twitch Live client")

