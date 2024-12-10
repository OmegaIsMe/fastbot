import asyncio
import logging
from dataclasses import KW_ONLY, asdict, dataclass
from functools import cache, cached_property
from typing import Any, ClassVar, Dict, Iterable, Literal, Self, Tuple, Type

from fastbot.bot import FastBot
from fastbot.event import Context, Event, MetaClass
from fastbot.message import Message, MessageSegment


@dataclass
class MessageEvent(Event):
    _: KW_ONLY

    message_type: Literal["group", "private"]
    post_type: Literal["message"] = "message"

    @classmethod
    @cache
    def subcalsses(cls) -> Dict[str, Type["MessageEvent"]]:
        return {subclass.message_type: subclass for subclass in cls.__subclasses__()}

    @classmethod
    def build_from(cls, *, ctx: Context) -> "MessageEvent":
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
    @dataclass
    class Sender(metaclass=MetaClass):
        user_id: int
        nickname: str
        sex: str
        age: int

        def __init__(self, **kwargs) -> None:
            pass

    _: KW_ONLY

    sub_type: Literal["friend", "group", "other"]
    message_id: int
    user_id: int
    message: Message
    raw_message: str
    font: int
    sender: Sender

    futures: ClassVar[Dict[int, asyncio.Future]] = {}

    message_type: ClassVar[Literal["private"]] = "private"

    def __init__(self, **kwargs) -> None:
        logging.debug(self.__repr__())

        self.message = Message(
            MessageSegment(type=msg["type"], data=msg["data"]) for msg in self.message
        )
        self.sender = self.Sender(**self.ctx["sender"])

        self.hash_value = hash(
            (self.user_id, self.time, self.self_id, self.raw_message)
        )

        if future := self.__class__.futures.get(self.user_id):
            future.set_result(self)

    def __hash__(self) -> int:
        return self.hash_value

    async def send(
        self,
        message: str
        | Message
        | MessageSegment
        | Iterable[str | Message | MessageSegment],
    ) -> Any:
        return await FastBot.do(
            endpoint="send_private_msg",
            message=[asdict(msg) for msg in Message(message)],
            self_id=self.self_id,
            user_id=self.user_id,
        )

    async def defer(
        self,
        message: str
        | Message
        | MessageSegment
        | Iterable[str | Message | MessageSegment],
    ) -> Self:
        future = asyncio.Future()
        self.__class__.futures[self.user_id] = future

        await self.send(message=message)

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
    @dataclass
    class Sender(metaclass=MetaClass):
        user_id: int | None = None
        nickname: str | None = None
        card: str | None = None
        sex: str | None = None
        age: int | None = None
        area: str | None = None
        level: str | None = None
        role: str | None = None
        title: str | None = None

        def __init__(self, **kwargs) -> None:
            pass

    _: KW_ONLY

    sub_type: Literal["normal", "anonymous", "notice"]
    message_id: int
    group_id: int
    user_id: int
    message: Message
    raw_message: str
    font: int
    sender: Sender

    futures: ClassVar[Dict[Tuple[int, int], asyncio.Future]] = {}

    message_type: ClassVar[Literal["group"]] = "group"

    def __init__(self, **kwargs) -> None:
        logging.debug(self.__repr__())

        self.message = Message(
            MessageSegment(type=msg["type"], data=msg["data"]) for msg in self.message
        )
        self.sender = self.Sender(**self.ctx.get("sender", {}))

        self.hash_value = hash(
            (self.user_id, self.time, self.self_id, self.raw_message)
        )

        if future := self.__class__.futures.get((self.group_id, self.user_id)):
            future.set_result(self)

    def __hash__(self) -> int:
        return self.hash_value

    async def send(
        self,
        message: str
        | Message
        | MessageSegment
        | Iterable[str | Message | MessageSegment],
    ) -> Any:
        return await FastBot.do(
            endpoint="send_group_msg",
            message=[asdict(msg) for msg in Message(message)],
            self_id=self.self_id,
            group_id=self.group_id,
        )

    async def defer(
        self,
        message: str
        | Message
        | MessageSegment
        | Iterable[str | Message | MessageSegment],
    ) -> Self:
        future = asyncio.Future()
        self.__class__.futures[(self.group_id, self.user_id)] = future

        await self.send(message=message)

        try:
            return await future
        finally:
            del self.__class__.futures[(self.group_id, self.user_id)]

    @cached_property
    def text(self) -> str:
        return "".join(
            segment.data["text"] for segment in self.message if segment.type == "text"
        )
