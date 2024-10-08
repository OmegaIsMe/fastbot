import logging
from dataclasses import KW_ONLY, dataclass
from functools import cache
from textwrap import shorten
from typing import Any, Dict, Literal, Self

from fastbot.event import Context, Event


@dataclass
class RequestEvent(Event):
    _: KW_ONLY

    request_type: str
    post_type: Literal["request"] = "request"

    @classmethod
    @cache
    def subcalsses(cls) -> Dict[str, Any]:
        return {subclass.request_type: subclass for subclass in cls.__subclasses__()}

    @classmethod
    def build_from(cls, *, ctx: Context) -> Self:
        if subclass := cls.subcalsses().get(ctx["request_type"]):
            return subclass(ctx=ctx, **ctx)

        return cls(
            ctx=ctx,
            time=ctx["time"],
            self_id=ctx["self_id"],
            request_type=ctx["request_type"],
        )


@dataclass
class FriendRequestEvent(RequestEvent):
    _: KW_ONLY

    time: int
    self_id: int
    user_id: int
    comment: str
    flag: str

    post_type: Literal["request"] = "request"
    request_type: Literal["friend"] = "friend"

    def __post_init__(self) -> None:
        logging.info(
            shorten(
                f"[{self.__class__.__name__}][User={self.user_id}]: {self.comment}",
                width=79,
                placeholder="...",
            )
        )

    async def approve(self, *, remark: str | None = None) -> Any:
        return await self.bot.do(
            endpoint="set_friend_add_request",
            self_id=self.self_id,
            approve=True,
            flag=self.flag,
            remark=remark,
        )

    async def reject(self) -> Any:
        return await self.bot.do(
            endpoint="set_friend_add_request", self_id=self.self_id, approve=False
        )


@dataclass
class GroupRequestEvent(RequestEvent):
    _: KW_ONLY

    time: int
    self_id: int
    sub_type: Literal["add", "invite"]
    group_id: int
    user_id: int
    comment: str
    flag: str

    post_type: Literal["request"] = "request"
    request_type: Literal["group"] = "group"

    def __post_init__(self) -> None:
        logging.info(
            shorten(
                f"[{self.__class__.__name__}][User={self.user_id}][Group={self.group_id}]: {self.comment}",
                width=79,
                placeholder="...",
            )
        )

    async def approve(self) -> Any:
        return await self.bot.do(
            endpoint="set_group_add_request",
            self_id=self.self_id,
            approve=True,
            sub_type=self.sub_type,
        )

    async def reject(self, *, reason: str | None = None) -> Any:
        return await self.bot.do(
            endpoint="set_group_add_request",
            self_id=self.self_id,
            approve=False,
            reason=reason,
        )
