from dataclasses import dataclass

EPSILON_TOKEN = "ε"


@dataclass(frozen=True)
class ParseNode:
    symbol: str
    token: str | None = None
    children: tuple["ParseNode", ...] = ()
