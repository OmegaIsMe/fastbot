from fastbot.event import Context
from fastbot.event.message import GroupMessageEvent, PrivateMessageEvent
from fastbot.matcher import Matcher, CommandMatcher
from fastbot.plugin import PluginManager, event_preprocessing, on


@event_preprocessing()
async def preprocessing(ctx: Context):
    # print(ctx)
    pass


@on(matcher=CommandMatcher({'你好', '早上好'}))
async def func(
    # The event type to be handled must be specified via type hints
    # You can use `|`  or `typing.Union` types
    event: GroupMessageEvent | PrivateMessageEvent,
) -> None:
    # print(event.text)
    await event.send('Start guessing the number game now: [0-10]!')
