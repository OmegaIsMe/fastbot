# FastBot

a lightweight bot framework base on `FastAPI` and `OneBot v11` protocol.

## Quick Start
### Installation
#### Install from pypi
```sh
pip install --no-cache --upgrade fastbot
```
#### Install from Github
```sh
pip install --no-cache --upgrade https://github.com/omegaisme/fastbot.git
```

### Example
The directory structure is as follows:
```sh
bot_example
|   __init__.py
|   bot.py
|
\---plugins
        __init__.py
        plugin_example.py
```

#### bot.py
```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastbot.bot import FastBot


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.add_api_websocket_route("/onebot/v11", FastBot.ws_adapter) # Register a websocket adapter to `FastAPI`
    yield


if __name__ == "__main__":
    (
        FastBot
        .build_app(lifespan=lifespan)  # Parameter will pass to `FastAPI(...)`
        .load_plugins("plugins")  # Parameter will pass to `fastbot.plugin.PluginManager.import_from(...)`
        .run(host="0.0.0.0", port=80)  # Parameter will pass to `uvicorn.run(...)`
    )
```

#### plugin_example.py

```python
from fastbot.event import Context
from fastbot.event.message import GroupMessageEvent, PrivateMessageEvent
from fastbot.matcher import Matcher
from fastbot.plugin import PluginManager, event_preprocessing, on

# Passing rules to the matcher
IsNotGroupAdmin = Matcher(rule=lambda event: event.sender.role != "admin")


# Refactoring the Matcher
class IsInGroupBlacklist(Matcher):
    def __init__(self, *blacklist):
        self.blacklist = blacklist

    def __call__(self, event: GroupMessageEvent) -> bool:
        return event.group_id in self.blacklist


# If all processors have a priority of 0, all processors will be executed concurrently,
# otherwise they will be executed in sequence.
@event_preprocessing(priority=0)
async def preprocessing(ctx: Context):
    if ctx.get("group_id") == ...:
        # In event processing, temporarily close the plugin
        PluginManager.plugins["plugins.plugin_example"].state.set(False)


# Combining multiple rules via `&(and)`, `|(or)`,`~(not)`
@on(matcher=IsNotGroupAdmin & IsInGroupBlacklist(...))
# For the best performance, you can use `callable function`
# E.g. `lambda event: event.get("group_id") in (...)`
async def func(
    # The event type to be handled must be specified via type hints
    # You can use `|`  or `typing.Union` types
    event: GroupMessageEvent | PrivateMessageEvent,
) -> None:
    if event.text == "guess":
        await event.send("Start guessing the number game now: [0-10]!")

        while new_event := await event.defer("Enter a number: "):
            if new_event.text != "10":
                await new_event.send("Guess wrong!")
                continue

            await new_event.send("Guess right!")
            return
```
