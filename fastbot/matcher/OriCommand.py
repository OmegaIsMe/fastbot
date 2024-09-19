from functools import reduce
from typing import Iterable, Set
from weakref import WeakKeyDictionary

from fastbot.event.message import GroupMessageEvent, PrivateMessageEvent
from fastbot.matcher import Matcher
from fastbot.message import Message, MessageSegment

class Command(Matcher):
    __slots__ = ("command", "sep", "strip")

    cache: WeakKeyDictionary[GroupMessageEvent | PrivateMessageEvent, Set[str]] = (
        WeakKeyDictionary()
    )

    def __init__(
        self, *, command: str | Iterable[str], sep: str = " ", strip: bool = False
    ) -> None:
        self.command = set(
            filter(None, command.split(sep) if isinstance(command, str) else command)
        )
        self.sep = sep
        self.strip = strip

    def __call__(self, event: GroupMessageEvent | PrivateMessageEvent) -> bool:
        if not (cmd := self.__class__.cache.get(event)):
            self.__class__.cache[event] = cmd = set(event.text.split(self.sep))

        if matched := bool(cmd & self.command):
            if self.strip:
                self.__class__.cache[event] = cmd - self.command

                event.message = Message(
                    (
                        MessageSegment.text(
                            text=reduce(
                                lambda text, command: text.replace(command, "").strip(),
                                self.command,
                                segment.data["text"],
                            )
                        )
                        if segment.type == "text"
                        else segment
                    )
                    for segment in event.message
                )

                del event.__dict__["text"]

        return matched