from __future__ import annotations

import logging

from types import TracebackType
from typing import AsyncContextManager, Type, cast

import httpx
from websockets import client
from websockets.exceptions import ConnectionClosed
from websockets.legacy.client import WebSocketClientProtocol
from websockets.typing import Subprotocol

from ._browser import Channel, ChannelClosed


class WebSocketChannel:
    def __init__(self, url: str) -> None:
        url = url.replace("http://", "ws://").replace("https://", "wss://")
        self._connection = client.connect(
            url,
            subprotocols=[Subprotocol("broadway")],
            open_timeout=None,
            ping_timeout=None,
            close_timeout=None,
            max_size=2**32,
        )

        self._open_connection: WebSocketClientProtocol | None = None

    async def __aenter__(self) -> "WebSocketChannel":
        self._open_connection = await self._connection
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if not self._open_connection:
            return

        await self._open_connection.close()
        self._open_connection = None

    async def receive_bytes(self) -> bytes:
        try:
            if not self._open_connection:
                return bytes()

            return cast(bytes, await self._open_connection.recv())
        except ConnectionClosed:
            raise ChannelClosed()

    async def send_bytes(self, data: bytes) -> None:
        try:
            if not self._open_connection:
                return

            await self._open_connection.send(data)
        except ConnectionClosed:
            raise ChannelClosed()


class HttpBrowserClient:
    def __init__(self, address: str) -> None:
        self.address = address

    async def get(self, resource: str) -> bytes:
        try:
            async with httpx.AsyncClient(base_url=self.address) as client:
                response = await client.get(resource)
                return response.content
        except Exception as ex:
            logging.error(f"Tried to connect to {self.address}")
            logging.error(f"Requested resource {resource}")
            raise ConnectionError from ex

    def open_channel(self) -> AsyncContextManager[Channel]:
        return WebSocketChannel(self.address + "/socket")
