from __future__ import annotations

from typing import Any


def load_hocon_config_text(text: str) -> dict[str, Any]:
    from pyhocon import ConfigFactory

    return ConfigFactory.parse_string(text, resolve=True).as_plain_ordered_dict()
