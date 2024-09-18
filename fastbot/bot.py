import asyncio
import logging
import os
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar, Iterable, Self
from weakref import WeakValueDictionary

from fastapi import FastAPI, WebSocket, WebSocketException, status

from fastbot.exception import APIException

try:
    import ujson as json

    json.dumps = partial(json.dumps, ensure_ascii=False, sort_keys=False)

except ImportError:
    import json

    json.dumps = partial(
        json.dumps, ensure_ascii=False, separators=(",", ":"), sort_keys=False
    )

if TYPE_CHECKING:
    from fastbot.event import Context


@dataclass
class FastBot:
    app: ClassVar[FastAPI]

    connector: ClassVar[WeakValueDictionary[str, WebSocket]] = WeakValueDictionary()
    futures: ClassVar[WeakValueDictionary[int, asyncio.Future]] = WeakValueDictionary()

    def __init__(self, app: FastAPI | None = None, *args, **kwargs) -> None:
        self.__class__.app = app or FastAPI(*args, **kwargs)

    @classmethod
    async def ws_adapter(cls, websocket: WebSocket) -> None:
        if authorization := os.getenv("FASTBOT_AUTHORIZATION"):
            if not (access_token := websocket.headers.get("authorization")):
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Missing `authorization` header",
                )

            match access_token.split():
                case [header, token] if header.title() in (
                    "Bear",
                    "Token",
                ) and token != authorization:
                    raise WebSocketException(
                        code=status.HTTP_403_FORBIDDEN,
                        reason="Invalid `authorization` header",
                    )

                case [token] if token != authorization:
                    raise WebSocketException(
                        code=status.HTTP_403_FORBIDDEN,
                        reason="Invalid `authorization` header",
                    )

                case _:
                    raise WebSocketException(
                        code=status.HTTP_403_FORBIDDEN,
                        reason="Invalid `authorization` header",
                    )

        if not (self_id := websocket.headers.get("x-self-id")):
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Missing `x-self-id` header",
            )

        if self_id in cls.connector:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Duplicate `x-self-id` header",
            )

        await websocket.accept()

        logging.info(f"Websocket connected {self_id=}")

        cls.connector[self_id] = websocket

        async for data in websocket.iter_text():
            asyncio.create_task(cls.event_handler(ctx=json.loads(data)))

        logging.warning(f"Websocket disconnected {self_id=}")

    @classmethod
    async def event_handler(cls, ctx: "Context") -> None:
        from fastbot.plugin import PluginManager

        try:
            if "post_type" in ctx:
                await PluginManager.run(ctx=ctx)

            else:
                (
                    cls.futures[ctx["echo"]].set_result(ctx.get("data"))
                    if ctx["status"] != "fail"
                    else cls.futures[ctx["echo"]].set_exception(APIException(ctx))
                )

        except Exception as e:
            logging.exception(e)

    @classmethod
    async def do(cls, *, endpoint: str, self_id: int, **kwargs) -> Any:
        future = asyncio.Future()
        future_id = id(future)

        logging.debug(f"{endpoint=} {self_id=} {kwargs=}")

        cls.futures[future_id] = future

        await cls.connector[str(self_id)].send_text(
            json.dumps({"action": endpoint, "params": kwargs, "echo": future_id})
        )

        return await future

    @classmethod
    def build(
        cls,
        app: FastAPI | None = None,
        plugins: str | Iterable[str] = "plugins",
        *args,
        **kwargs,
    ) -> Self:
        from fastbot.plugin import PluginManager

        if isinstance(plugins, str):
            PluginManager.import_from(plugins)
        else:
            for plugin in plugins:
                PluginManager.import_from(plugin)

        return cls(app=app, *args, **kwargs)

    @classmethod
    def run(cls, *args, **kwargs) -> None:
        import uvicorn

        uvicorn.run(cls.app, *args, **kwargs)
