import asyncio
import logging
from dataclasses import KW_ONLY, asdict, dataclass
from functools import cache, cached_property
from typing import Any, ClassVar, Dict, List, Literal, Self, Tuple

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

    post_type: ClassVar[Literal["message"]] = "message"
    message_type: ClassVar[Literal["private"]] = "private"

    class Sender:
        def __init__(
            self, user_id: int, nickname: str, sex: str, age: int, **kwargs
        ) -> None:
            self.user_id = user_id
            self.nickname = nickname
            self.sex = sex
            self.age = age

            for k, v in kwargs.items():
                setattr(self, k, v)

    def __init__(
        self,
        *,
        ctx: Context,
        time: int,
        self_id: int,
        sub_type: Literal["friend", "group", "other"],
        message_id: int,
        user_id: int,
        message: List[Dict[str, Any]],
        raw_message: str,
        font: int,
        sender: Dict,
        **kwargs,
    ) -> None:
        self.ctx = ctx

        self.time = time
        self.self_id = self_id
        self.sub_type = sub_type
        self.message_id = message_id
        self.user_id = user_id
        self.message = Message(
            MessageSegment(type=msg["type"], data=msg["data"]) for msg in message
        )
        self.raw_message = raw_message
        self.font = font
        self.sender = self.Sender(**sender)

        for k, v in kwargs.items():
            setattr(self, k, v)

        if future := self.__class__.futures.get(self.user_id):
            future.set_result(self)

        logging.debug(self.__repr__())

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
    futures: ClassVar[Dict[Tuple[int, int], asyncio.Future]] = {}

    post_type: ClassVar[Literal["message"]] = "message"
    message_type: ClassVar[Literal["group"]] = "group"

    class Anonymous:
        def __init__(
            self,
            id: int | None = None,
            name: str | None = None,
            flag: str | None = None,
            **kwargs,
        ) -> None:
            self.id = id
            self.name = name
            self.flag = flag

            for k, v in kwargs.items():
                setattr(self, k, v)

    class Sender:
        def __init__(
            self,
            user_id: int | None = None,
            nickname: str | None = None,
            card: str | None = None,
            sex: str | None = None,
            age: int | None = None,
            area: str | None = None,
            level: str | None = None,
            role: str | None = None,
            title: str | None = None,
            **kwargs,
        ) -> None:
            self.user_id = user_id
            self.nickname = nickname
            self.card = card
            self.sex = sex
            self.age = age
            self.area = area
            self.level = level
            self.role = role
            self.title = title

            for k, v in kwargs.items():
                setattr(self, k, v)

    def __init__(
        self,
        ctx: Context,
        time: int,
        self_id: int,
        sub_type: Literal["normal", "anonymous", "notice"],
        message_id: int,
        group_id: int,
        user_id: int,
        message: List[Dict],
        raw_message: str,
        font: int,
        sender: Dict,
        anonymous: Dict = {},
        **kwargs,
    ) -> None:
        self.ctx = ctx

        self.time = time
        self.self_id = self_id
        self.sub_type = sub_type
        self.message_id = message_id
        self.group_id = group_id
        self.user_id = user_id
        self.message = Message(
            MessageSegment(type=msg["type"], data=msg["data"]) for msg in message
        )
        self.raw_message = raw_message
        self.font = font
        self.sender = self.Sender(**sender)
        self.anonymous = self.Anonymous(**anonymous)

        for k, v in kwargs.items():
            setattr(self, k, v)

        if future := self.__class__.futures.get((self.group_id, self.user_id)):
            future.set_result(self)

        logging.debug(self.__repr__())

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
