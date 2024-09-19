import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from contextvars import ContextVar
from dataclasses import KW_ONLY, dataclass, field
from importlib.util import module_from_spec, spec_from_file_location
from operator import attrgetter
from pathlib import Path
from types import SimpleNamespace, UnionType
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    ClassVar,
    Dict,
    List,
    _UnionGenericAlias,  # type: ignore
    get_args,
)

from fastbot.event import Context, Event
from fastbot.event.message import GroupMessageEvent, PrivateMessageEvent
from fastbot.matcher import Matcher


@dataclass
class Plugin:
    _: KW_ONLY

    module_name: str
    module_path: str

    state: ContextVar = ContextVar('state', default=True)

    preprocessors: List[SimpleNamespace] = field(default_factory=list)
    postprocessors: List[SimpleNamespace] = field(default_factory=list)

    executors: List[Callable[..., Any]] = field(default_factory=list)

    async def run(self, event: Event) -> None:
        await asyncio.gather(*(executor(event) for executor in self.executors))


@dataclass
class PluginManager:
    plugins: ClassVar[Dict[str, Plugin]] = {}
    aggrate_matchers: ClassVar[Dict[str, Matcher]] = {}
    """聚合匹配器"""

    @classmethod
    def import_from(cls, path_to_import: str) -> None:
        def load(module_name: str, module_path: str) -> None:
            if spec := spec_from_file_location(module_name, module_path):
                module = module_from_spec(spec)

                try:
                    plugin = Plugin(module_name=module_name, module_path=module_path)
                    cls.plugins[module_name] = plugin

                    spec.loader.exec_module(module)  # type: ignore
                    logging.info(f'loaded plugin [{module_name}] from [{module_path}]')

                except Exception as e:
                    logging.exception(e)

                    del cls.plugins[module_name]

                finally:
                    if not (len(plugin.preprocessors) + len(plugin.executors) + len(plugin.postprocessors)):
                        del cls.plugins[module_name]

        if (path := Path(path_to_import)).is_file() and path.name.endswith('.py') and not path.name.startswith('_'):
            load('.'.join(path.parts).removesuffix('.py'), str(path))

        elif path.is_dir():
            for file in path.rglob('*.py'):
                if file.is_file() and not file.name.startswith('_'):
                    load(
                        '.'.join(file.relative_to(path.parent).parts).removesuffix('.py'),
                        str(file),
                    )

    @classmethod
    @asynccontextmanager
    async def event_hook(cls, *, ctx: Context) -> AsyncGenerator[Context, None]:
        for proc in sorted(
            (proc for plugin in cls.plugins.values() for proc in plugin.preprocessors),
            key=attrgetter('priority'),
        ):
            await (func(ctx) if asyncio.iscoroutinefunction(func := proc.func) else asyncio.to_thread(func, ctx))

        yield ctx

        for proc in sorted(
            (proc for plugin in cls.plugins.values() for proc in plugin.postprocessors),
            key=attrgetter('priority'),
        ):
            await (func(ctx) if asyncio.iscoroutinefunction(func := proc.func) else asyncio.to_thread(func, ctx))

    @classmethod
    async def run(cls, *, ctx: Context) -> None:
        async with cls.event_hook(ctx=ctx) as ctx:
            event = Event.build_from(ctx=ctx)

            if isinstance(event, GroupMessageEvent):
                if future := event.futures.get((event.group_id, event.user_id)):
                    future.set_result(event)

            elif isinstance(event, PrivateMessageEvent):
                if future := event.futures.get(event.user_id):
                    future.set_result(event)

            await asyncio.gather(*(plugin.run(event) for plugin in cls.plugins.values() if plugin.state.get()))

            callbacks = []
            for matcher in cls.aggrate_matchers.values():
                if cbs := matcher(event):
                    callbacks.extend(cbs)
            await asyncio.gather(*(callback(event) for callback in callbacks))


def event_preprocessing(*, priority: int = 0) -> Callable[..., Any]:
    def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        PluginManager.plugins[func.__module__].preprocessors.append(SimpleNamespace(priority=priority, func=func))
        return func

    return wrapper


def event_postprocessing(*, priority: int = 0) -> Callable[..., Any]:
    def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        PluginManager.plugins[func.__module__].postprocessors.append(SimpleNamespace(priority=priority, func=func))
        return func

    return wrapper


def on(matcher: Matcher | Callable[[Event], bool] | None = None):
    if matcher:
        if matcher.is_aggrated is True:

            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                PluginManager.aggrate_matchers[matcher.__class__.__name__] = matcher
                matcher.aggrate(func)
                return func

        else:

            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                event_type = tuple()

                for param in func.__annotations__.values():
                    if isinstance(param, (UnionType, _UnionGenericAlias)):
                        for arg in get_args(param):
                            with suppress(TypeError):
                                if issubclass(arg, Event):
                                    event_type += (arg,)
                    else:
                        with suppress(TypeError):
                            if issubclass(param, Event):
                                event_type += (param,)

                event_type = tuple(event_type)

                async def wrapper(event: Event, *args, **kwargs) -> Any:
                    if not isinstance(event, event_type) or not matcher(event):
                        return

                    return await func(event, *args, **kwargs)

                PluginManager.plugins[func.__module__].executors.append(wrapper)

                return wrapper
    else:

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            event_type = tuple()

            for param in func.__annotations__.values():
                if isinstance(param, (UnionType, _UnionGenericAlias)):
                    for arg in get_args(param):
                        with suppress(TypeError):
                            if issubclass(arg, Event):
                                event_type += (arg,)
                else:
                    with suppress(TypeError):
                        if issubclass(param, Event):
                            event_type += (param,)

            async def wrapper(event: Event, *args, **kwargs) -> Any:
                if not isinstance(event, event_type):
                    return

                return await func(event, *args, **kwargs)

            PluginManager.plugins[func.__module__].executors.append(wrapper)

            return wrapper

    return decorator
