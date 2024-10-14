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

    middlewares: List[Middleware] = field(default_factory=list)
    executors: List[Callable[..., Any]] = field(default_factory=list)

    async def run(self, event: Event) -> None:
        await asyncio.gather(*(executor(event) for executor in self.executors))


@dataclass
class PluginManager:
    plugins: ClassVar[Dict[str, Plugin]] = {}

    @classmethod
    def import_from(cls, path_to_import: str) -> None:
        def load(module_name: str, module_path: str) -> None:
            try:
                spec = spec_from_file_location(module_name, module_path)
                module = module_from_spec(spec)  # type: ignore

                cls.plugins[module_name] = Plugin()

                spec.loader.exec_module(module)  # type: ignore

                logging.info(f"loaded plugin [{module_name}] from [{module_path}]")

            except Exception as e:
                logging.exception(e)

            finally:
                if not any(
                    cls.plugins[module_name].middlewares
                    + cls.plugins[module_name].executors
                ):
                    del cls.plugins[module_name]

        if (
            (path := Path(path_to_import)).is_file()
            and path.name.endswith(".py")
            and not path.name.startswith("_")
        ):
            load(".".join(path.parts).removesuffix(".py"), str(path))

        elif path.is_dir():
            for file in path.rglob("*.py"):
                if file.is_file() and not file.name.startswith("_"):
                    load(
                        ".".join(file.relative_to(path.parent).parts).removesuffix(
                            ".py"
                        ),
                        str(file),
                    )

    @classmethod
    @cache
    def middlewares(cls) -> List[Plugin.Middleware]:
        return sorted(
            middleware
            for plugin in cls.plugins.values()
            for middleware in plugin.middlewares
        )

    @classmethod
    async def run(cls, *, ctx: Context) -> None:
        for middleware in cls.middlewares():
            await (
                func(ctx)
                if asyncio.iscoroutinefunction(func := middleware.executor)
                else asyncio.to_thread(func, ctx)
            )

            if not ctx:
                return

        event = Event.build_from(ctx=ctx)

        await asyncio.gather(
            *(
                plugin.run(event)
                for plugin in cls.plugins.values()
                if plugin.state.get()
            )
        )


def middleware(*, priority: int = 0) -> Callable[..., Any]:
    def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        PluginManager.plugins[func.__module__].middlewares.append(
            Plugin.Middleware(priority=priority, executor=func)
        )

        return func

    return wrapper


def on(matcher: Matcher | Callable[[Event], bool] | None = None):
    if matcher:

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            event_type = tuple()

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

            @wraps(func)
            async def wrapper(event: Event) -> Callable[[Event], Any] | None:
                if not (isinstance(event, event_type) and matcher(event)):
                    return

                return await func(event)

            PluginManager.plugins[func.__module__].executors.append(wrapper)

            return wrapper

    else:

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            event_type = tuple()

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

            @wraps(func)
            async def wrapper(event: Event) -> Callable[[Event], Any] | None:
                if not isinstance(event, event_type):
                    return

                return await func(event)

            PluginManager.plugins[func.__module__].executors.append(wrapper)

            return wrapper

    return decorator
