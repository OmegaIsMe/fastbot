import logging
from dataclasses import KW_ONLY, dataclass
from functools import cache
from typing import Dict, Literal, Type

from fastbot.event import Context, Event, MetaClass


@dataclass
class MetaEvent(Event):
    _: KW_ONLY

    meta_event_type: Literal["heartbeat", "lifecycle"]
    post_type: Literal["meta_event"] = "meta_event"

    @classmethod
    @cache
    def subcalsses(cls) -> Dict[str, Type["MetaEvent"]]:
        return {subclass.meta_event_type: subclass for subclass in cls.__subclasses__()}

    @classmethod
    def build_from(cls, *, ctx: Context) -> "MetaEvent":
        if subclass := cls.subcalsses().get(ctx["meta_event_type"]):
            return subclass(ctx=ctx, **ctx)

        return cls(
            ctx=ctx,
            time=ctx["time"],
            self_id=ctx["self_id"],
            meta_event_type=ctx["meta_event_type"],
        )


@dataclass
class LifecycleMetaEvent(MetaEvent):
    _: KW_ONLY

    time: int
    self_id: int
    sub_type: Literal["enable", "disable", "connect"]

    meta_event_type: Literal["lifecycle"] = "lifecycle"

    def __init__(self, **kwargs) -> None:
        logging.debug(self.__repr__())


@dataclass
class HeartbeatMetaEvent(MetaEvent):
    @dataclass
    class Status(metaclass=MetaClass):
        pass

    _: KW_ONLY

    time: int
    self_id: int
    status: Status
    interval: int

    meta_event_type: Literal["heartbeat"] = "heartbeat"

    def __init__(self, **kwargs) -> None:
        logging.debug(self.__repr__())

        self.status = self.Status(**self.ctx["status"])
