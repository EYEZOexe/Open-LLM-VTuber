import abc

class LivePlatformInterface(abc.ABC):
    def __init__(self):
        self._websocket = None
        self._is_connected = False  # Use private attribute to avoid property conflicts
        self._running = True

    @abc.abstractmethod
    async def connect(self):
        pass

    @abc.abstractmethod
    async def disconnect(self):
        pass

    @abc.abstractmethod
    async def run(self):
        pass
