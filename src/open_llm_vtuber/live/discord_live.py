import asyncio
import json
import logging
import websockets
import discord
import re
import os
from datetime import datetime
from src.open_llm_vtuber.live.live_interface import LivePlatformInterface

logger = logging.getLogger(__name__)

class DiscordLive(LivePlatformInterface):
    """
    Discord live platform integration for Open-LLM-VTuber.
    Handles connection to Discord, message forwarding, and proxy communication.
    """
    THINKING_MESSAGE = "Thinking..."
    STREAMING_MESSAGE = "can't talk right now streaming!"
    MAX_REPLY_LENGTH = 4000

    def __init__(self, token: str, character_name: str, handle_platform_event=None):
        self.token = token
        self.character_name = character_name
        self._handle_platform_event = handle_platform_event
        self.discord_client = None
        self._websocket = None
        self._running = True
        self.last_message = None
        self._message_handler = None
        self.thinking_message = None
        self._message_handlers = []  # Add this for handler registration

    @property
    def is_connected(self) -> bool:
        return self._websocket is not None and not getattr(self._websocket, 'closed', False)

    async def connect(self, proxy_url: str = "ws://127.0.0.1:12393/proxy-ws") -> bool:
        """
        Connect to the proxy WebSocket and start Discord bot client.
        """
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                self._websocket = await websockets.connect(proxy_url)
                logger.info(f"src.open_llm_vtuber.live.discord_live:connect:{attempt} - Connected to proxy WebSocket")
                break
            except Exception as e:
                logger.error(f"Failed to connect to proxy WebSocket (attempt {attempt}): {e}")
                await asyncio.sleep(2 * attempt)
        else:
            logger.critical("Could not connect to proxy WebSocket after multiple attempts.")
            return False
        # Start DiscordBot and proxy response listener
        try:
            self.discord_client = DiscordBot(self.token, self.character_name, self._handle_platform_event or self._handle_platform_event_internal)
            loop = asyncio.get_running_loop()
            loop.create_task(self.discord_client.start(self.token))
            # Register send_reply_to_discord as a message handler
            await self.register_message_handler(self.send_reply_to_discord)
            loop.create_task(self.start_receiving())
            logger.info("DiscordBot background task started.")
        except Exception as e:
            logger.error(f"Failed to start DiscordBot: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        return True

    async def disconnect(self) -> None:
        """
        Disconnect from proxy and Discord client.
        """
        if self._websocket:
            await self._websocket.close()
        if self.discord_client:
            await self.discord_client.close()

    async def send_message(self, text: str) -> bool:
        return await self._send_to_proxy(text)

    async def _send_to_proxy(self, text: str) -> bool:
        if not self.is_connected or not self._websocket or getattr(self._websocket, 'closed', False):
            logger.error("Cannot send message: Not connected to proxy (websocket closed)")
            return False
        try:
            payload = {"type": "text-input", "text": text}
            await self._websocket.send(json.dumps(payload))
            logger.info(f"src.open_llm_vtuber.live.discord_live:_send_to_proxy - Sent formatted message to proxy: {payload}")
            return True
        except Exception as e:
            logger.error(f"Error sending to proxy: {e}")
            return False

    async def register_message_handler(self, handler):
        self._message_handlers.append(handler)

    async def _call_message_handlers(self, response):
        for handler in self._message_handlers:
            try:
                await handler(response)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

    async def start_receiving(self) -> None:
        while self.is_connected and self._websocket:
            try:
                response = await self._websocket.recv()
                logger.info(f"src.open_llm_vtuber.live.discord_live:start_receiving - Received response from proxy: {response}")
                await self._call_message_handlers(response)
            except Exception as e:
                logger.error(f"Error receiving from proxy: {e}")
                break

    async def send_reply_to_discord(self, response: str) -> None:
        """
        Handle and send a reply to Discord based on the proxy response.
        Handles JSON and fallback string responses, message cleanup, and chat history.
        """
        if not self.last_message:
            return
        username = getattr(self.last_message.author, 'name', 'unknown_user')
        logger.info(f"[Discord] send_reply_to_discord received: {response}")

        reply_text, is_final = self._parse_proxy_response(response)
        if reply_text is None:
            logger.info("Skipping reply: reply_text is None")
            return
        if not is_final or len(reply_text) > self.MAX_REPLY_LENGTH or reply_text.strip().lower() == self.THINKING_MESSAGE.lower():
            logger.info(f"Skipping reply: is_final={is_final}, len={len(reply_text)}, text={reply_text}")
            return

        reply_text = self._clean_reply_text(reply_text)
        # Commented out: await self.save_chat_history(username, reply_text, is_bot=True)
        await self._delete_thinking_message()
        await self.last_message.channel.send(reply_text)
        self.last_message = None
        self.thinking_message = None

    def _clean_reply_text(self, text: str) -> str:
        """
        Remove emotes in square brackets and strip whitespace.
        """
        return re.sub(r"\[[^\]]*\]", "", text).strip()

    async def _delete_thinking_message(self) -> None:
        if self.thinking_message:
            try:
                await self.thinking_message.delete()
                logger.info("Deleted Thinking... message before sending AI reply.")
            except Exception as e:
                logger.error(f"Failed to delete Thinking... message: {e}")

    async def run(self) -> None:
        await self.connect()
        while self._running and self.is_connected:
            await asyncio.sleep(1)
        await self.disconnect()

    async def _handle_platform_event_internal(self, event_data):
        message_text = event_data.get('message')
        discord_message = event_data.get('discord_message')
        username = getattr(discord_message.author, 'name', 'unknown_user') if discord_message else 'unknown_user'
        import os
        live_lock_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'live.lock')
        live_is_running = os.path.exists(live_lock_path)
        if not message_text:
            return
        logger.info(f"src.open_llm_vtuber.live.discord_live:_handle_platform_event_internal - Received from Discord: {message_text}")
        # Only set self.thinking_message ONCE here, do not send an extra 'Thinking...' message
        target_message = self.last_message or discord_message
        self.last_message = target_message
        if not target_message:
            logger.warning("No valid Discord message to reply to for 'Thinking...'")
            return
        try:
            if live_is_running:
                self.thinking_message = await target_message.channel.send(self.STREAMING_MESSAGE)
                return
            else:
                self.thinking_message = await target_message.channel.send(self.THINKING_MESSAGE)
                logger.info("Sent 'Thinking...' message in DM.")
        except Exception as e:
            logger.error(f"Failed to send Thinking... message: {e}")
        # Always send to proxy, do not require character name mention
        await self._send_to_proxy(message_text)

    async def handle_incoming_messages(self, message):
        logger.info(f"src.open_llm_vtuber.live.discord_live:handle_incoming_messages - Handling incoming message: {message}")
        # Forward to Discord user if possible
        await self.send_reply_to_discord(message)

    def _parse_proxy_response(self, response: str):
        """
        Parse the proxy response and extract reply text and is_final flag.
        Returns (reply_text, is_final:bool)
        """
        try:
            data = json.loads(response)
            logger.info(f"[Discord] send_reply_to_discord parsed JSON: {data}")
            if data.get("type") == "full-text":
                return data.get("text", ""), data.get("is_final", True)
            else:
                logger.info(f"Ignoring non-user message type: {data.get('type')}")
                return None, False
        except Exception as e:
            logger.warning(f"Could not parse response as JSON: {response} | Exception: {e}")
            # Fallback: If not JSON, check if this is likely the AI response (not a control message)
            if response and len(response) < self.MAX_REPLY_LENGTH and not response.strip().startswith('{') and not response.strip().startswith('['):
                return response, True
            return None, False

class DiscordBot(discord.Client):
    def __init__(self, token, character_name, event_callback):
        intents = discord.Intents.default()
        intents.messages = True
        intents.dm_messages = True
        intents.message_content = True  # Required for message content
        super().__init__(intents=intents)
        self.token = token
        self.character_name = character_name
        self.event_callback = event_callback

    async def on_ready(self):
        logger.info(f"Discord bot is online as: {self.user} (ID: {self.user.id})")
        print(f"Discord bot is online as: {self.user} (ID: {self.user.id})")

    async def on_message(self, message):
        logger.info(f"[Discord] Received message: '{message.content}' from '{message.author}' in '{message.channel}' (DM: {message.guild is None})")
        print(f"[Discord] Received message: '{message.content}' from '{message.author}' in '{message.channel}' (DM: {message.guild is None})")
        if message.author == self.user:
            return
        event_data = {
            "message": message.content,
            "discord_message": message,
            "platform": "discord"
        }
        await self.event_callback(event_data)

    async def close(self):
        await super().close()
