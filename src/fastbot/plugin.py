import asyncio
import logging
from contextlib import suppress
from contextvars import ContextVar
from dataclasses import KW_ONLY, dataclass, field
from functools import cache, wraps
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import UnionType
from typing import Any, Callable, ClassVar, Dict, List, Union, get_args, get_origin

from fastbot.event import Context, Event
from fastbot.matcher import Matcher


@dataclass
class Plugin:
    @dataclass(order=True)
    class Middleware:
        _: KW_ONLY

        priority: int = 0
        executor: Callable[[Context], Any] = field(compare=False)

    _: KW_ONLY

    state: ContextVar = ContextVar("state", default=True)

    init: Callable | None = None

    middlewares: List[Middleware] = field(default_factory=list)
    executors: List[Callable[..., Any]] = field(default_factory=list)

    async def run(self, event: Event) -> None:
        await asyncio.gather(*(executor(event) for executor in self.executors))


@dataclass
class PluginManager:
    plugins: ClassVar[Dict[str, Plugin]] = {}

    @classmethod
    def import_from(cls, path_to_import: str) -> None:
        def load(module_name: str, module_path: Path) -> None:
            cls.plugins[module_name] = plugin = Plugin()

            try:
                spec = spec_from_file_location(module_name, module_path)
                module = module_from_spec(spec)  # type: ignore

                spec.loader.exec_module(module)  # type: ignore

                if init := getattr(module, "init", None):
                    plugin.init = init

                logging.info(f"loaded plugin [{module_name}] from [{module_path}]")

            except Exception as e:
                logging.exception(e)

            finally:
                if not (plugin.init or plugin.middlewares or plugin.executors):
                    del cls.plugins[module_name]

        if (path := Path(path_to_import)).is_dir():
            for file in path.rglob("*.py"):
                if file.is_file() and not file.name.startswith("_"):
                    load(
                        ".".join(file.relative_to(path.parent).parts).removesuffix(
                            ".py"
                        ),
                        file,
                    )

        elif (
            path.is_file()
            and path.name.endswith(".py")
            and not path.name.startswith("_")
        ):
            load(".".join(path.parts).removesuffix(".py"), path)

    @classmethod
    @cache
    def middlewares(cls) -> List[Callable[[Context], Any]]:
        return [
            func.executor
            for func in sorted(
                middleware
                for plugin in cls.plugins.values()
                for middleware in plugin.middlewares
            )
        ]

    @classmethod
    async def run(cls, *, ctx: Context) -> None:
        for middleware in cls.middlewares():
            _ = asyncio.Task(
                middleware(ctx), loop=asyncio.get_running_loop(), eager_start=True
            )

            if not ctx:
                return

        event = Event.build_from(ctx=ctx)

        await asyncio.gather(
            *(
                plugin.run(event=event)
                for plugin in cls.plugins.values()
                if plugin.state.get()
            )
        )


def middleware(*, priority: int = 0) -> Callable[..., Any]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        PluginManager.plugins[func.__module__].middlewares.append(
            Plugin.Middleware(priority=priority, executor=func)
        )

        return func

    return decorator


def on(matcher: Matcher | Callable[..., bool] | None = None) -> Callable[..., Any]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        event_type = ()

        for param in func.__annotations__.values():
            if get_origin(param) in (Union, UnionType):
                for arg in get_args(param):
                    with suppress(TypeError):
                        if issubclass(arg, Event):
                            event_type += (arg,)

            else:
                with suppress(TypeError):
                    if issubclass(param, Event):
                        event_type += (param,)

        if matcher:

            @wraps(func)
            async def wrapper(event: Event) -> Any:
                if isinstance(event, event_type) and matcher(event):
                    return await func(event)
        else:

            @wraps(func)
            async def wrapper(event: Event) -> Any:
                if isinstance(event, event_type):
                    return await func(event)

        PluginManager.plugins[func.__module__].executors.append(wrapper)

        return wrapper

    return decorator
