from dataclasses import KW_ONLY, dataclass
from functools import cache
from typing import Any, Dict, Literal, Self, TypeAlias

Context: TypeAlias = Dict[str, Any]


@dataclass
class Event:
    _: KW_ONLY

    ctx: Context

    time: int
    self_id: int
    post_type: Literal["message", "notice", "request", "meta_event"]

    @classmethod
    @cache
    def subcalsses(cls) -> Dict[str, Any]:
        return {subclass.post_type: subclass for subclass in cls.__subclasses__()}

    @classmethod
    def build_from(cls, *, ctx: Context) -> Self:
        if subclass := cls.subcalsses().get(ctx["post_type"]):
            return subclass.build_from(ctx=ctx)

        return cls(
            ctx=ctx,
            time=ctx["time"],
            self_id=ctx["self_id"],
            post_type=ctx["post_type"],
        )
