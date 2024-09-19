from .BaseMatcher import Matcher
from ..event.message import GroupMessageEvent, PrivateMessageEvent
from typing import Callable, ClassVar, Dict


class AggratesMatcher(Matcher):
    is_aggrated = True

    def aggrate(self, callback: Callable):
        raise NotImplementedError


class CommandMatcher(AggratesMatcher):
    SEP = ' '
    callbacks: ClassVar[Dict[str, list[Callable]]] = {}

    def __init__(self, cmds: set[str]):
        self.cmds = cmds

    def aggrate(self, callback: Callable):
        for cmd in self.cmds:
            prev = CommandMatcher.callbacks.get(cmd)
            if prev is None:
                prev = []
                CommandMatcher.callbacks[cmd] = prev
            prev.append(callback)

    def __call__(self, event: GroupMessageEvent | PrivateMessageEvent, *args, **kwargs) -> bool:
        if not event.text:
            return []
        cmds = event.text.split(self.SEP)
        return CommandMatcher.callbacks.get(cmds[0])
