import logging
from dataclasses import KW_ONLY, dataclass
from functools import cache
from typing import Dict, Literal, Type

from fastbot.event import Context, Event, MetaClass


@dataclass
class NoticeEvent(Event):
    _: KW_ONLY

    notice_type: str
    post_type: Literal["notice"] = "notice"

    @classmethod
    @cache
    def subcalsses(cls) -> Dict[str, Type["NoticeEvent"]]:
        return {subclass.notice_type: subclass for subclass in cls.__subclasses__()}

    @classmethod
    def build_from(cls, *, ctx: Context) -> "NoticeEvent":
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
    class File(metaclass=MetaClass):
        _: KW_ONLY

        id: str
        name: str
        size: int
        busid: int

        def __init__(self, **kwargs) -> None:
            pass

    _: KW_ONLY

    time: int
    self_id: int
    group_id: int
    user_id: int
    file: File

    notice_type: Literal["group_upload"] = "group_upload"

    def __init__(self, **kwargs) -> None:
        logging.debug(self.__repr__())

        self.file = self.File(**self.ctx.get("file", {}))


@dataclass
class GroupAdminChangeNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    sub_type: Literal["set", "unset"]
    group_id: int
    user_id: int

    notice_type: Literal["group_admin"] = "group_admin"

    def __init__(self, **kwargs) -> None:
        logging.debug(self.__repr__())


@dataclass
class GroupMemberDecreaseNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    sub_type: Literal["leave", "kick", "kick_me"]
    group_id: int
    user_id: int
    operator_id: int

    notice_type: Literal["group_decrease"] = "group_decrease"

    def __init__(self, **kwargs) -> None:
        logging.debug(self.__repr__())


@dataclass
class GroupMemberIncreaseNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    sub_type: Literal["approve", "invite"]
    group_id: int
    operator_id: int
    user_id: int

    notice_type: Literal["group_increase"] = "group_increase"

    def __init__(self, **kwargs) -> None:
        logging.debug(self.__repr__())


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

    notice_type: Literal["group_ban"] = "group_ban"

    def __init__(self, **kwargs) -> None:
        logging.debug(self.__repr__())


@dataclass
class FriendAddNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    user_id: int

    notice_type: Literal["friend_add"] = "friend_add"

    def __init__(self, **kwargs) -> None:
        logging.debug(self.__repr__())


@dataclass
class GroupMessageRecallNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    group_id: int
    user_id: int
    operator_id: int
    message_id: int

    notice_type: Literal["group_recall"] = "group_recall"

    def __init__(self, **kwargs) -> None:
        logging.debug(self.__repr__())


@dataclass
class FriendMessageRecallNoticeEvent(NoticeEvent):
    _: KW_ONLY

    time: int
    self_id: int
    user_id: int
    message_id: int

    notice_type: Literal["friend_recall"] = "friend_recall"

    def __init__(self, **kwargs) -> None:
        logging.debug(self.__repr__())
