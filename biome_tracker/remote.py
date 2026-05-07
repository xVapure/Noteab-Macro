

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union


RemoteCommandType = Literal[
    "__rejoin__",
    "__check_merchant__",
    "__screenshot__",
    "__reroll__",
    "use_item",
]


@dataclass(frozen=True)
class RemoteCommand:

    command: RemoteCommandType
    payload: str


def to_legacy_tuple(cmd: RemoteCommand) -> tuple[str, Union[str, int]]:
    if cmd.command == "use_item":
        item, _, amount = cmd.payload.partition(":")
        try:
            return (item, int(amount or "1"))
        except ValueError:
            return (item, 1)
    return (cmd.command, cmd.payload)
