from pathlib import Path

import pytest

from flockr.config import load_config_file

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_hocon_resolves_same_document_substitutions() -> None:
    pytest.importorskip("pyhocon")

    config = load_config_file(FIXTURES_DIR / "sample-config.conf")

    assert config["trading"]["shard"]["shard1"]["primary"] == {
        "host": "testhost1",
        "directory": "/local/1/app/test/shard_1",
    }
    assert config["trading"]["shard"]["shard1"]["channelFilter"] == {
        "trading": "Symbol=A*",
        "common": "Symbol=A*",
        "listMessage": "_NO_FILTER_",
        "marketDataSnapshot": "Symbol=A*",
        "deskGroup": "DeskGroup=TEST",
    }
