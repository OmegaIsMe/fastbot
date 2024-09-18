import asyncio
import logging
from dataclasses import KW_ONLY, asdict, dataclass
from functools import cache, cached_property
from textwrap import shorten
from typing import Any, ClassVar, Dict, Literal, Self, Tuple

from fastbot.bot import FastBot
from fastbot.event import Context, Event
from fastbot.message import Message, MessageSegment


@dataclass
class MessageEvent(Event):
    _: KW_ONLY

    message_type: str
    post_type: Literal["message"] = "message"

    @classmethod
    @cache
    def subcalsses(cls) -> Dict[str, Any]:
        return {subclass.message_type: subclass for subclass in cls.__subclasses__()}

    @classmethod
    def build_from(cls, *, ctx: Context) -> Self:
        if subclass := cls.subcalsses().get(ctx["message_type"]):
            return subclass(ctx=ctx, **ctx)

        return cls(
            ctx=ctx,
            time=ctx["time"],
            self_id=ctx["self_id"],
            post_type=ctx["post_type"],
            message_type=ctx["message_type"],
        )


@dataclass
class PrivateMessageEvent(MessageEvent):
    futures: ClassVar[Dict[int, asyncio.Future]] = {}

    @dataclass
    class Sender:
        _: KW_ONLY

        user_id: int | None = None
        nickname: str | None = None
        sex: str | None = None
        age: int | None = None

    _: KW_ONLY

    time: int
    self_id: int
    sub_type: Literal["friend", "group", "other"]
    message_id: int
    user_id: int
    message: Message
    raw_message: str
    font: int
    sender: Sender

    # go-cqhttp
    message_seq: int

    # napcat
    real_id: int
    message_format: str

    post_type: Literal["message"] = "message"
    message_type: Literal["private"] = "private"

    def __post_init__(self) -> None:
        self.sender = self.__class__.Sender(**(self.ctx["sender"] or {}))
        self.message = Message(
            MessageSegment(type=msg["type"], data=msg["data"])
            for msg in self.ctx["message"]
        ).compact()

        logging.info(
            shorten(
                f"[{self.__class__.__name__}][Sender={self.sender.nickname}({self.user_id})]: {self.text}",
                width=79,
                placeholder="...",
            )
        )

    def __hash__(self) -> int:
        return hash((self.user_id, self.time, self.self_id, self.raw_message))

    async def send(self, message: str | Message | MessageSegment) -> Any:
        return await FastBot.do(
            endpoint="send_private_msg ",
            message=[asdict(msg) for msg in Message(message).compact()],
            self_id=self.self_id,
            user_id=self.user_id,
        )

    async def defer(self, message: str | Message | MessageSegment) -> Self:
        await self.send(message=message)

        future = asyncio.Future()
        self.__class__.futures[self.user_id] = future

        try:
            return await future
        finally:
            del self.__class__.futures[self.user_id]

    @cached_property
    def text(self) -> str:
        return "".join(
            segment.data["text"] for segment in self.message if segment.type == "text"
        )


@dataclass
class GroupMessageEvent(MessageEvent):
    futures: ClassVar[Dict[Tuple[int, int], asyncio.Future]] = {}

    @dataclass
    class Anonymous:
        _: KW_ONLY

        id: int | None = None
        name: str | None = None
        flag: str | None = None

    @dataclass
    class Sender:
        _: KW_ONLY

        user_id: int | None = None
        nickname: str | None = None
        card: str | None = None
        sex: str | None = None
        age: int | None = None
        area: str | None = None
        level: str | None = None
        role: str | None = None
        title: str | None = None

    _: KW_ONLY

    time: int
    self_id: int
    sub_type: Literal["normal", "anonymous", "notice"]
    message_id: int
    group_id: int
    user_id: int
    message: Message
    raw_message: str
    font: int
    sender: Sender

    # go-cqhttp
    message_seq: int

    # napcat
    real_id: int
    message_format: str

    anonymous: Anonymous | None = None
    post_type: Literal["message"] = "message"
    message_type: Literal["group"] = "group"

    def __post_init__(self) -> None:
        self.anonymous = self.__class__.Anonymous(
            **(self.ctx.get("anonymous", {}) or {})
        )
        self.sender = self.__class__.Sender(**(self.ctx["sender"] or {}))
        self.message = Message(
            MessageSegment(type=msg["type"], data=msg["data"])
            for msg in self.ctx["message"]
        ).compact()

        logging.info(
            shorten(
                f"[{self.__class__.__name__}][Group={self.group_id}][Sender={self.sender.nickname}({self.user_id})]: {self.text}",
                width=79,
                placeholder="...",
            )
        )

    def __hash__(self) -> int:
        return hash(
            (self.group_id, self.user_id, self.self_id, self.time, self.raw_message)
        )

    async def send(self, message: str | MessageSegment | Message) -> Any:
        return await FastBot.do(
            endpoint="send_group_msg",
            message=[asdict(msg) for msg in Message(message).compact()],
            self_id=self.self_id,
            group_id=self.group_id,
        )

    async def defer(self, message: str | Message | MessageSegment) -> Self:
        await self.send(message=message)

        future = asyncio.Future()
        self.__class__.futures[(self.group_id, self.user_id)] = future

        try:
            return await future
        finally:
            del self.__class__.futures[(self.group_id, self.user_id)]

    @cached_property
    def text(self) -> str:
        return "".join(
            segment.data["text"] for segment in self.message if segment.type == "text"
        )
