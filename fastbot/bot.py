import asyncio
import logging
import os
from dataclasses import dataclass
from functools import partial
from typing import Any, ClassVar, Dict, Iterable, Self

from fastapi import FastAPI, WebSocket, WebSocketException, status

from fastbot.event import Context
from fastbot.plugin import PluginManager

try:
    import ujson as json

    json.dumps = partial(json.dumps, ensure_ascii=False, sort_keys=False)

except ImportError:
    import json

    json.dumps = partial(
        json.dumps, ensure_ascii=False, separators=(",", ":"), sort_keys=False
    )


@dataclass
class FastBot:
    app: ClassVar[FastAPI]

    connectors: ClassVar[Dict[int, WebSocket]] = {}
    futures: ClassVar[Dict[int, asyncio.Future]] = {}

    def __init__(self, app: FastAPI | None = None, **kwargs) -> None:
        self.__class__.app = app or FastAPI(**kwargs)

    @classmethod
    async def ws_adapter(cls, websocket: WebSocket) -> None:
        if authorization := os.getenv("FASTBOT_AUTHORIZATION"):
            if not (access_token := websocket.headers.get("authorization")):
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Missing `authorization` header",
                )

            match access_token.split():
                case [header, token] if header.title() in ("Bearer", "Token"):
                    if token != authorization:
                        raise WebSocketException(
                            code=status.HTTP_403_FORBIDDEN,
                            reason="Invalid `authorization` header",
                        )

                case [token]:
                    if token != authorization:
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

        if not (self_id.isdigit() and (self_id := int(self_id))):
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid `x-self-id` header",
            )

        if self_id in cls.connectors:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Duplicate `x-self-id` header",
            )

        await websocket.accept()

        logging.info(f"Websocket connected {self_id=}")

        cls.connectors[self_id] = websocket

        try:
            while True:
                match message := await websocket.receive():
                    case {"bytes": data} | {"text": data}:
                        _ = asyncio.Task(
                            cls.event_handler(ctx=json.loads(data)),
                            loop=asyncio.get_running_loop(),
                            eager_start=True,
                        )

                    case _:
                        logging.warning(f"Unknow websocket message received {message=}")

        except Exception as e:
            logging.exception(e)

        finally:
            logging.warning(f"Websocket disconnected {self_id=}")
            del cls.connectors[int(self_id)]

    @classmethod
    async def event_handler(cls, ctx: Context) -> None:
        try:
            if "post_type" in ctx:
                await PluginManager.run(ctx=ctx)

            else:
                (
                    cls.futures[ctx["echo"]].set_result(ctx.get("data"))
                    if ctx["status"] == "ok"
                    else cls.futures[ctx["echo"]].set_exception(RuntimeError(ctx))
                )

        except Exception as e:
            logging.exception(e)

    @classmethod
    async def do(cls, *, endpoint: str, self_id: int | None = None, **kwargs) -> Any:
        if not self_id:
            if len(cls.connectors) == 1:
                self_id = next(iter(cls.connectors))

            else:
                raise RuntimeError("Parameter `self_id` must be specified")

        logging.debug(f"{endpoint=} {self_id=} {kwargs=}")

        future = asyncio.Future()
        future_id = id(future)

        cls.futures[future_id] = future

        try:
            await cls.connectors[self_id].send_bytes(
                json.dumps(
                    {"action": endpoint, "params": kwargs, "echo": future_id}
                ).encode(encoding="utf-8")
            )

            return await future

        except Exception as e:
            logging.exception(e)

        finally:
            del cls.futures[future_id]

    @classmethod
    def build(
        cls,
        app: FastAPI | None = None,
        plugins: str | Iterable[str] | None = None,
        **kwargs,
    ) -> Self:
        if isinstance(plugins, str):
            PluginManager.import_from(plugins)

        elif isinstance(plugins, Iterable):
            for plugin in plugins:
                PluginManager.import_from(plugin)

        return cls(app=app, **kwargs)

    @classmethod
    def run(cls, **kwargs) -> None:
        import uvicorn

        uvicorn.run(app=cls.app, **kwargs)
