from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self


@dataclass(frozen=True)
class ContextFrame:
    values: dict[str, Any] = field(default_factory=dict)
    parent: ContextFrame | None = None

    def child(self, values: dict[str, Any] | None = None) -> Self:
        return type(self)(values=values or {}, parent=self)

    def get(self, path: str) -> Any:
        head, *tail = path.split(".")
        value = self._get_name(head)

        for segment in tail:
            value = _get_child(value, segment)

        return value

    def flatten(self) -> dict[str, Any]:
        if self.parent is None:
            return dict(self.values)

        merged = self.parent.flatten()
        merged.update(self.values)
        return merged

    def _get_name(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]

        if self.parent is not None:
            return self.parent._get_name(name)

        raise KeyError(name)


def _get_child(value: Any, segment: str) -> Any:
    if isinstance(value, dict):
        return value[segment]

    if isinstance(value, list):
        return value[int(segment)]

    return getattr(value, segment)
