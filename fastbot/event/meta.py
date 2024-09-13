from dataclasses import KW_ONLY, dataclass
from functools import cache
from types import SimpleNamespace
from typing import Any, Dict, Literal, Self

from fastbot.event import Context, Event


@dataclass
class MetaEvent(Event):
    _: KW_ONLY

    meta_event_type: str
    post_type: Literal["meta_event"] = "meta_event"

    @classmethod
    @cache
    def subcalsses(cls) -> Dict[str, Any]:
        return {subclass.meta_event_type: subclass for subclass in cls.__subclasses__()}

    @classmethod
    def build_from(cls, *, ctx: Context) -> Self:
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

    post_type: Literal["meta_event"] = "meta_event"
    meta_event_type: Literal["lifecycle"] = "lifecycle"


@dataclass
class HeartbeatMetaEvent(MetaEvent):
    _: KW_ONLY

    time: int
    self_id: int
    status: SimpleNamespace
    interval: int

    post_type: Literal["meta_event"] = "meta_event"
    meta_event_type: Literal["heartbeat"] = "heartbeat"
