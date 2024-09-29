from dataclasses import KW_ONLY, dataclass
from functools import cache
from typing import Any, Dict, Literal, Self

from fastbot.event import Context, Event


@dataclass
class NoticeEvent(Event):
    _: KW_ONLY

    notice_type: str
    post_type: Literal["notice"] = "notice"

    @classmethod
    @cache
    def subcalsses(cls) -> Dict[str, Any]:
        return {subclass.notice_type: subclass for subclass in cls.__subclasses__()}

    @classmethod
    def build_from(cls, *, ctx: Context) -> Self:
        if subclass := cls.subcalsses().get(ctx["notice_type"]):
            return subclass(ctx=ctx, **ctx)

        return cls(
            ctx=ctx,
            time=ctx["time"],
            self_id=ctx["self_id"],
            notice_type=ctx["notice_type"],
        )


@dataclass
class GroupFileUploadNoticeEvent(NoticeEvent):
    @dataclass
    class File:
        _: KW_ONLY

        id: str
        name: str
        size: int
        busid: int

    _: KW_ONLY

    time: int
    self_id: int
    group_id: int
    user_id: int
    file: File

    post_type: Literal["notice"] = "notice"
    notice_type: Literal["group_upload"] = "group_upload"

    def __post_init__(self) -> None:
        self.file = self.__class__.File(**(self.ctx["file"] or {}))


@dataclass
class GroupAdminChangeNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    sub_type: Literal["set", "unset"]
    group_id: int
    user_id: int

    post_type: Literal["notice"] = "notice"
    notice_type: Literal["group_admin"] = "group_admin"


@dataclass
class GroupMemberDecreaseNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    sub_type: Literal["leave", "kick", "kick_me"]
    group_id: int
    user_id: int
    operator_id: int

    post_type: Literal["notice"] = "notice"
    notice_type: Literal["group_decrease"] = "group_decrease"


@dataclass
class GroupMemberIncreaseNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    sub_type: Literal["approve", "invite"]
    group_id: int
    operator_id: int
    user_id: int

    post_type: Literal["notice"] = "notice"
    notice_type: Literal["group_increase"] = "group_increase"


@dataclass
class GroupBanNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    sub_type: Literal["ban", "lift_ban"]
    group_id: int
    operator_id: int
    user_id: int
    duration: int

    post_type: Literal["notice"] = "notice"
    notice_type: Literal["group_ban"] = "group_ban"


@dataclass
class FriendAddNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    user_id: int

    post_type: Literal["notice"] = "notice"
    notice_type: Literal["friend_add"] = "friend_add"


@dataclass
class GroupMessageRecallNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    group_id: int
    user_id: int
    operator_id: int
    message_id: int

    post_type: Literal["notice"] = "notice"
    notice_type: Literal["group_recall"] = "group_recall"


@dataclass
class FriendMessageRecallNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    user_id: int
    message_id: int

    post_type: Literal["notice"] = "notice"
    notice_type: Literal["friend_recall"] = "friend_recall"
