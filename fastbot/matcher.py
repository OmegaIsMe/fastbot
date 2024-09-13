import logging
from dataclasses import KW_ONLY, dataclass, field
from typing import Callable, List


@dataclass
class Matcher:
    _: KW_ONLY

    rule: Callable[..., bool] = lambda: True
    matchers: List["Matcher"] = field(default_factory=list)
    operator: str | None = None

    def __call__(self, *args, **kwargs) -> bool:
        try:
            if self.operator:
                if self.operator == "and":
                    return all(matcher(*args, **kwargs) for matcher in self.matchers)
                elif self.operator == "or":
                    return any(matcher(*args, **kwargs) for matcher in self.matchers)
                else:
                    raise ValueError(f"Invalid operator: {self.operator}")
            else:
                return self.rule(*args, **kwargs)
        except Exception as e:
            logging.exception(f"Error in matcher: {self.rule.__name__}: {e}")
            return False

    def __and__(self, other: "Matcher") -> "Matcher":
        if self.operator == "and":
            self.matchers.append(other)
            return self
        else:
            return Matcher(matchers=[self, other], operator="and")

    def __or__(self, other: "Matcher") -> "Matcher":
        if self.operator == "or":
            self.matchers.append(other)
            return self
        else:
            return Matcher(matchers=[self, other], operator="or")

    def __invert__(self) -> "Matcher":
        return Matcher(rule=lambda *args, **kwargs: not self(*args, **kwargs))

    def __repr__(self) -> str:
        if self.operator:
            matchers_str = ", ".join([m.rule.__name__ for m in self.matchers])
            return f"Match({self.operator}, [{matchers_str}])"
        else:
            return f"Match({self.rule.__name__})"
