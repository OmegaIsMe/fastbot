import asyncio
import logging
import os
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Self, Type

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

    connector: ClassVar[Dict[str, WebSocket]] = {}
    futures: ClassVar[Dict[int, asyncio.Future]] = {}

    @classmethod
    async def ws_adapter(cls, websocket: WebSocket) -> None:
        if authorization := os.getenv("FASTBOT_AUTHORIZATION"):
            if not (access_token := websocket.headers.get("authorization")):
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="missing `authorization` header",
                )

            match access_token.split():
                case [header, token] if header.title() in (
                    "Bear",
                    "Token",
                ) and token != authorization:
                    raise WebSocketException(
                        code=status.HTTP_403_FORBIDDEN,
                        reason="invalid `authorization` header",
                    )

                case [token] if token != authorization:
                    raise WebSocketException(
                        code=status.HTTP_403_FORBIDDEN,
                        reason="invalid `authorization` header",
                    )

                case _:
                    raise WebSocketException(
                        code=status.HTTP_403_FORBIDDEN,
                        reason="invalid `authorization` header",
                    )

        if not (self_id := websocket.headers.get("x-self-id")):
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="missing `x-self-id` header",
            )

        if self_id in cls.connector:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="duplicate `x-self-id` header",
            )

        await websocket.accept()

        logging.info(f"websocket connected {self_id=}")

        cls.connector[self_id] = websocket

        try:
            async for data in websocket.iter_text():
                asyncio.create_task(cls.event_handler(ctx=json.loads(data)))

        except Exception as e:
            logging.exception(e)

        finally:
            logging.warning(f"websocket disconnected {self_id=}")

            del cls.connector[self_id]

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

        try:
            cls.futures[future_id] = future

            await cls.connector[str(self_id)].send_text(
                json.dumps({"action": endpoint, "params": kwargs, "echo": future_id})
            )

            return await future

        finally:
            del cls.futures[future_id]

    @classmethod
    def build_app(cls, app: FastAPI | None = None, *args, **kwargs) -> Type[Self]:
        cls.app = app or FastAPI(*args, **kwargs)
        return cls

    @classmethod
    def load_plugins(cls, path_to_plugins: str = "plugins") -> Type[Self]:
        from fastbot.plugin import PluginManager

        PluginManager.import_from(path_to_plugins)
        return cls

    @classmethod
    def run(cls, *args, **kwargs) -> None:
        import uvicorn

        if not cls.app:
            cls.build_app()

        uvicorn.run(app=cls.app, *args, **kwargs)
