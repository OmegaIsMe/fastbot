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

        self.length = 0
        self.maxlen = maxlen

        if iterable:
            self.extend(iterable)

    def __iter__(self) -> Iterator[Any]:
        next_node = self[NEXT]

        while next_node is not self:
            yield next_node[DATA]
            next_node = next_node[NEXT]

    def __len__(self) -> int:
        return self.length

    def __delitem__(self, idx: int) -> None:
        if not (-self.length <= idx < self.length):
            raise IndexError("index out of range")

        if idx < 0:
            idx += self.length

        if idx <= self.length // 2:
            current_node = self[NEXT]
            for _ in range(idx):
                current_node = current_node[NEXT]
        else:
            current_node = self[PREV]
            for _ in range(self.length - 1 - idx):
                current_node = current_node[PREV]

        prev_node = current_node[PREV]
        next_node = current_node[NEXT]
        prev_node[NEXT] = next_node
        next_node[PREV] = prev_node

        self.length -= 1

    def append(self, value: Any) -> None:
        if self.maxlen is not None and self.length == self.maxlen:
            self.popleft()

        prev_node = self[PREV]
        prev_node[NEXT] = self[PREV] = [prev_node, self, value]

        self.length += 1

    def appendleft(self, value: Any) -> None:
        if self.maxlen is not None and self.length == self.maxlen:
            self.pop()

        next_node = self[NEXT]
        next_node[PREV] = self[NEXT] = [self, next_node, value]

        self.length += 1

    def clear(self) -> None:
        self[:] = [self, self, None]
        self.length = 0

    def extend(self, values: Any) -> None:
        for value in values:
            self.append(value)

    def extendleft(self, values: Any) -> None:
        for value in values:
            self.appendleft(value)

    def insert(self, idx: int, value: Any) -> None:
        if not (-self.length <= idx < self.length):
            raise IndexError("index out of range")

        if self.maxlen is not None and self.length == self.maxlen:
            raise IndexError("list has reached its maximum length")

        if idx == 0:
            self.appendleft(value)

        elif idx < 0:
            idx += self.length

        if idx <= self.length // 2:
            current_node = self[NEXT]
            for _ in range(idx):
                current_node = current_node[NEXT]

        else:
            current_node = self
            for _ in range(self.length - idx):
                current_node = current_node[PREV]

        prev_node = current_node
        next_node = current_node[NEXT]
        link = [prev_node, next_node, value]
        next_node[PREV] = link
        prev_node[NEXT] = link

        self.length += 1

    def pop(self) -> Any:
        if self.length == 0:
            raise IndexError("pop from empty list")

        prev_node = self[PREV]
        prev_node[PREV][NEXT] = self
        self[PREV] = prev_node[PREV]

        self.length -= 1
        return prev_node[DATA]

    def popleft(self) -> Any:
        if self.length == 0:
            raise IndexError("pop from empty list")

        next_node = self[NEXT]
        next_node[NEXT][PREV] = self
        self[NEXT] = next_node[NEXT]

        self.length -= 1
        return next_node[DATA]

    def reverse(self) -> None:
        prev_node = self
        current_node = self[NEXT]
        self[NEXT] = self[PREV] = self

        while current_node is not self:
            next_node = current_node[NEXT]
            current_node[NEXT] = prev_node
            current_node[PREV] = prev_node
            prev_node = current_node
            current_node = next_node

        self[NEXT] = prev_node
        self[PREV] = prev_node[PREV]

    def remove(self, value: Any) -> None:
        current_node = self[NEXT]
        while current_node is not self:
            if current_node[DATA] == value:
                prev_node = current_node[PREV]
                next_node = current_node[NEXT]
                prev_node[NEXT] = next_node
                next_node[PREV] = prev_node

                self.length -= 1
                return

            current_node = current_node[NEXT]

        raise ValueError(f"{value} is not in list")

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
                prev_node = self[PREV]
                self[PREV] = prev_node[PREV]
                prev_node[PREV][NEXT] = self
                self[NEXT][PREV] = prev_node
                prev_node[NEXT] = self[NEXT]
                self[NEXT] = prev_node
                prev_node[PREV] = self

        else:
            for _ in range(length - n):
                next_node = self[NEXT]
                self[NEXT] = next_node[NEXT]
                next_node[NEXT][PREV] = self
                self[PREV][NEXT] = next_node
                next_node[PREV] = self[PREV]
                self[PREV] = next_node
                next_node[NEXT] = self


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
