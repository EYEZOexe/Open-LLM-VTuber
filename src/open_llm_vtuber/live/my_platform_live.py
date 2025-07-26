import asyncio
import json
import websockets
from loguru import logger
from twitchio import Client
from src.open_llm_vtuber.live.live_platform_interface import LivePlatformInterface

class TwitchLive(LivePlatformInterface):
    """
    Twitch live platform integration for Open-LLM-VTuber.
    Handles connection to Twitch, message forwarding, and proxy communication.
    """
    STREAMING_MESSAGE = "Currently live, can't talk atm (Twitch)"
    MAX_REPLY_LENGTH = 4000

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.channel: str = config.get("channel", "")
        self.token: str = config.get("token", "")
        self.bot_nick: str = config.get("bot_nick", "TwitchBot")
        self.character_name: str = config.get("character_name", "Mao")
        self._websocket = None
        self._running = True
        self.twitch_client = None
        self._message_handlers = []  # Support multiple handlers
        self._is_connected = False  # Internal state for is_connected

    @property
    def is_connected(self) -> bool:
        return self._is_connected and self._websocket is not None and not getattr(self._websocket, 'closed', False)

    async def connect(self, proxy_url: str = "ws://127.0.0.1:12393/proxy-ws") -> bool:
        """
        Connect to the proxy WebSocket and Twitch with retry.
        """
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                self._websocket = await websockets.connect(proxy_url)
                self._is_connected = True
                logger.info("Connected to proxy WebSocket")
                break
            except Exception as e:
                logger.error(f"Failed to connect to proxy WebSocket (attempt {attempt}): {e}")
                await asyncio.sleep(2 * attempt)
        else:
            logger.critical("Could not connect to proxy WebSocket after multiple attempts.")
            self._is_connected = False
            return False
        # Initialize Twitch client
        try:
            self.twitch_client = TwitchChatClient(self.token, self.channel, self.bot_nick, self._handle_platform_event)
            loop = asyncio.get_running_loop()
            loop.create_task(self.twitch_client.start())
            loop.create_task(self.start_receiving())
            logger.info(f"TwitchChatClient background task started for channel: {self.channel}")
        except Exception as e:
            logger.error(f"Failed to start TwitchChatClient: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self._is_connected = False
            return False
        return True

    async def disconnect(self) -> None:
        """
        Disconnect from all services.
        """
        self._is_connected = False
        if self._websocket:
            await self._websocket.close()
        if self.twitch_client:
            await self.twitch_client.close()

    async def send_message(self, text: str) -> bool:
        return await self._send_to_proxy(text)

    async def _send_to_proxy(self, text: str) -> bool:
        if not self.is_connected or not self._websocket or getattr(self._websocket, 'closed', False):
            logger.error("Cannot send message: Not connected to proxy (websocket closed)")
            return False
        try:
            payload = {"type": "text-input", "text": text}
            await self._websocket.send(json.dumps(payload))
            logger.info(f"Sent formatted message to proxy: {text}")
            return True
        except Exception as e:
            logger.error(f"Error sending to proxy: {e}")
            return False

    async def register_message_handler(self, handler):
        """Register a message handler callback."""
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
                # Only log errors, not every debug message
                # logger.debug(f"TwitchLive:start_receiving - Received response from proxy: {response}")
                await self._call_message_handlers(response)
                await self.send_reply_to_twitch(response)
            except Exception as e:
                logger.error(f"Error receiving from proxy: {e}")
                break

    async def send_reply_to_twitch(self, response: str) -> None:
        # Previous version: just pass (no filtering, no debug log)
        pass

    async def run(self) -> None:
        await self.connect()
        while self._running and self.is_connected:
            await asyncio.sleep(1)
        await self.disconnect()

    async def _handle_platform_event(self, event_data: dict):
        message_text = event_data.get('message')
        import os
        live_lock_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'live.lock')
        live_is_running = os.path.exists(live_lock_path)
        if message_text:
            logger.info(f"Received from Twitch: {message_text}")
            if live_is_running:
                logger.info(self.STREAMING_MESSAGE)
                return
            if self.character_name.lower() in message_text.lower():
                await self._send_to_proxy(message_text)

class TwitchChatClient(Client):
    def __init__(self, token, channel, bot_nick, event_callback):
        super().__init__(token=token, initial_channels=[channel])
        self.bot_nick = bot_nick
        self.event_callback = event_callback

    async def event_ready(self):
        logger.info(f"Twitch bot ready and joined channels: {[ch.name for ch in self.connected_channels]}")

    async def event_message(self, message):
        if message.echo:
            return
        event_data = {"message": message.content}
        await self.event_callback(event_data)

    async def close(self):
        if hasattr(self, '_ws') and self._ws:
            await self._ws.close()
        else:
            await super().close()
