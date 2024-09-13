from dataclasses import dataclass, field
from itertools import chain, groupby
from operator import attrgetter
from typing import Any, Dict, Iterable, Iterator, Literal, Self, Union

MessageSegmentData = Dict[str, Any]


PREV, NEXT, DATA = 0, 1, 2


class Link(list):
    def __init__(
        self, iterable: Iterable | None = None, maxlen: int | None = None
    ) -> None:
        self[:] = [self, self, None]

        self.maxlen = maxlen

        if iterable:
            self.extend(iterable)

        self.length = 0

    def clear(self) -> None:
        self[:] = [self, self, None]

    def append(self, value: Any) -> None:
        if self.maxlen is not None and self.length == self.maxlen:
            self.popleft()

        last = self[PREV]
        last[NEXT] = self[PREV] = [last, self, value]

        self.length += 1

    def appendleft(self, value: Any) -> None:
        if self.maxlen is not None and self.length == self.maxlen:
            self.pop()

        first = self[NEXT]
        first[PREV] = self[NEXT] = [self, first, value]

        self.length += 1

    def extend(self, values: Any) -> None:
        for value in values:
            self.append(value)

    def extendleft(self, values: Any) -> None:
        for value in values:
            self.appendleft(value)

    def pop(self) -> Any:
        if (last := self[PREV]) is self:
            raise IndexError("pop from empty list")

        prev = last[PREV]
        prev[NEXT] = self
        self[PREV] = prev

        self.length -= 1

        return last[DATA]

    def popleft(self) -> Any:
        if (first := self[NEXT]) is self:
            raise IndexError("pop from empty list")

        next = first[NEXT]
        self[NEXT] = next
        next[PREV] = self

        self.length -= 1

        return first[DATA]

    def rotate(self, n: int) -> None:
        if (length := self.length) == 0:
            return

        n %= length
        if n == 0:
            return

        if n < 0:
            n += length

        if n <= length // 2:
            for _ in range(n):
                last = self[PREV]
                self[PREV] = last[PREV]
                last[PREV][NEXT] = self
                self[NEXT][PREV] = last
                last[NEXT] = self[NEXT]
                self[NEXT] = last
                last[PREV] = self

        else:
            for _ in range(length - n):
                first = self[NEXT]
                self[NEXT] = first[NEXT]
                first[NEXT][PREV] = self
                self[PREV][NEXT] = first
                first[PREV] = self[PREV]
                self[PREV] = first
                first[NEXT] = self

    def __iter__(self) -> Iterator[Any]:
        first = self[NEXT]

        while first is not self:
            yield first[DATA]
            first = first[NEXT]

    def __len__(self) -> int:
        return self.length

    def index(self, x: Any, start: int = 0, end: int = -1) -> int:
        if end == -1 or end > self.length:
            end = self.length

        if start < 0:
            start = 0

        for idx, data in enumerate(self):
            if start <= idx < end:
                if data == x:
                    return idx

        raise ValueError(f"{x} is not in the list")

    def insert(self, i: int, x: Any) -> None:
        if self.maxlen is not None and self.length == self.maxlen:
            raise IndexError("This list has reached its maximum length")

        if i == 0:
            self.appendleft(x)

        elif i < 0:
            self.insert(self.length + i + 1, x)

        else:
            first = self[NEXT]
            for _ in range(i - 1):
                first = first[NEXT]

            prev = first
            next = first[NEXT]

            link = [prev, next, x]
            prev[NEXT] = link
            next[PREV] = link

            self.length += 1

    def reverse(self) -> None:
        prev = self
        first = self[NEXT]

        while first is not self:
            next_node = first[NEXT]
            first[NEXT] = prev
            prev = first
            first = next_node

        self[NEXT] = prev
        self[PREV] = prev


@dataclass
class MessageSegment:
    type: str
    data: MessageSegmentData = field(default_factory=dict)

    def __add__(self, other: Union[str, "MessageSegment", Iterable]) -> "Message":
        return Message(self) + other

    def __radd__(self, other: Union[str, "MessageSegment", Iterable]) -> "Message":
        return self + Message(other)

    @classmethod
    def text(cls, text: str) -> Self:
        return cls(type="text", data={"text": text})

    @classmethod
    def face(cls, id: int) -> Self:
        return cls(type="face", data={"id": str(id)})

    @classmethod
    def image(
        cls,
        file: str,
        type: Literal["flash"] | None = None,
        url: str | None = None,
        cache: bool | None = None,
        proxy: bool | None = None,
        timeout: int | None = None,
    ) -> Self:
        return cls(
            type="image",
            data={
                "file": file,
                "type": type,
                "url": url,
                "cache": cache,
                "proxy": proxy,
                "timeout": timeout,
            },
        )

    @classmethod
    def record(
        cls,
        file: str,
        magic: bool | None = None,
        url: str | None = None,
        cache: bool | None = None,
        proxy: bool | None = None,
        timeout: int | None = None,
    ) -> Self:
        return cls(
            type="record",
            data={
                "file": file,
                "magic": magic,
                "url": url,
                "cache": cache,
                "proxy": proxy,
                "timeout": timeout,
            },
        )

    @classmethod
    def video(
        cls,
        file: str,
        url: str | None = None,
        cache: bool | None = None,
        proxy: bool | None = None,
        timeout: int | None = None,
    ) -> Self:
        return cls(
            type="video",
            data={
                "file": file,
                "url": url,
                "cache": cache,
                "proxy": proxy,
                "timeout": timeout,
            },
        )

    @classmethod
    def at(cls, qq: int | Literal["all"]) -> Self:
        return cls(type="at", data={"qq": qq})

    @classmethod
    def rps(cls) -> Self:
        return cls(type="rps")

    @classmethod
    def dice(cls) -> Self:
        return cls(type="dice")

    @classmethod
    def shake(cls) -> Self:
        return cls(type="shake")

    @classmethod
    def poke(cls) -> Self:
        return cls(type="poke")

    @classmethod
    def anonymous(cls) -> Self:
        return cls(type="anonymous")

    @classmethod
    def share(
        cls, url: str, title: str, content: str | None = None, image: str | None = None
    ) -> Self:
        return cls(
            type="share",
            data={"url": url, "title": title, "content": content, "image": image},
        )

    @classmethod
    def contact(cls, type: Literal["qq", "group"], id: int) -> Self:
        return cls(type="contact", data={"type": type, "id": id})

    @classmethod
    def location(
        cls,
        lat: float,
        lon: float,
        title: str | None = None,
        content: str | None = None,
    ) -> Self:
        return cls(
            type="location",
            data={"lat": lat, "lon": lon, "title": title, "content": content},
        )

    @classmethod
    def music(
        cls,
        type: Literal["custom", "qq", "163", "xm"],
        id: int | None = None,
        url: str | None = None,
        audio: str | None = None,
        title: str | None = None,
        content: str | None = None,
        image: str | None = None,
    ) -> Self:
        return cls(
            type="music",
            data={
                "type": type,
                "id": id,
                "url": url,
                "audio": audio,
                "title": title,
                "content": content,
                "image": image,
            },
        )

    @classmethod
    def reply(cls, id: int) -> Self:
        return cls(type="reply", data={"id": id})

    @classmethod
    def forward(cls, id: int) -> Self:
        return cls(type="forward", data={"id": id})

    @classmethod
    def node(
        cls,
        id: int | None = None,
        user_id: int | None = None,
        nickname: str | None = None,
        content: Union[str, "Message", None] = None,
    ) -> Self:
        return cls(
            type="node",
            data={
                "id": id,
                "user_id": user_id,
                "nickname": nickname,
                "content": content,
            },
        )

    @classmethod
    def xml(cls, data: str) -> Self:
        return cls(type="xml", data={"data": data})

    @classmethod
    def json(cls, data: str) -> Self:
        return cls(type="json", data={"data": data})


class Message(Link):
    def __init__(self, content: str | MessageSegment | Iterable | None = None) -> None:
        super().__init__()

        if content:
            if isinstance(content, MessageSegment):
                self.append(content)
            elif isinstance(content, str):
                self.append(MessageSegment.text(text=content))
            elif isinstance(content, Iterable):
                self.extend(chain.from_iterable(Message(item) for item in content))

    def __add__(self, other: Union[str, MessageSegment, Iterable]) -> "Message":
        message = Message(self)
        message += other

        return message

    def __radd__(self, other: Union[str, MessageSegment, Iterable]) -> "Message":
        message = Message(other)
        message += self

        return message

    def __iadd__(self, other: Union[str, MessageSegment, Iterable]) -> "Message":
        if isinstance(other, Message):
            self.extend(other)
        elif isinstance(other, MessageSegment):
            self.append(other)
        elif isinstance(other, str):
            self.append(MessageSegment.text(text=other))
        elif isinstance(other, Iterable):
            self.extend(chain.from_iterable(Message(item) for item in other))

        return self

    def compact(self, *, concat: str = "") -> "Message":
        return Message(
            MessageSegment.text(
                concat.join(segment.data["text"] for segment in segments)
            )
            if key == "text"
            else segments
            for key, segments in groupby(self, key=attrgetter("type"))
        )
