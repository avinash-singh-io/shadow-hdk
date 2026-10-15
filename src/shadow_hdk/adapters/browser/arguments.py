"""One argument contract for the catalogue and every browser engine dispatch."""

from typing import Annotated, cast

from pydantic import BaseModel, ConfigDict, Field, JsonValue

READ_ACTIONS = ("snapshot", "find", "screenshot", "tabs", "console", "requests", "wait")
WRITE_ACTIONS = (
    "open",
    "back",
    "forward",
    "new_tab",
    "close_tab",
    "click",
    "type",
    "select",
    "press",
    "scroll",
)


class Inputs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    tab: str | None = Field(default=None, min_length=1, max_length=100)
    timeout_ms: int = Field(default=10000, ge=1, le=60000)
    url: str | None = Field(default=None, min_length=1, max_length=8192)
    selector: str | None = Field(default=None, min_length=1, max_length=4096)
    ref: str | None = Field(default=None, pattern=r"^@e[1-9][0-9]*$", max_length=100)
    role: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, max_length=4096)
    nth: int | None = Field(default=None, ge=0)
    value: str | None = Field(default=None, max_length=1_000_000)
    values: list[Annotated[str, Field(max_length=4096)]] | None = Field(
        default=None, max_length=1000
    )
    key: str | None = Field(default=None, min_length=1, max_length=100)
    x: float = Field(default=0, ge=-100000, le=100000)
    y: float = Field(default=0, ge=-100000, le=100000)
    full_page: bool = False


_PAGE = {"tab", "timeout_ms"}
_QUERY = {"selector", "role", "name"}
_TARGET = _QUERY | {"nth", "ref"}
FIELDS = {
    "tabs": set(),
    "console": {"tab"},
    "requests": {"tab"},
    "new_tab": {"url", "timeout_ms"},
    "open": _PAGE | {"url"},
    "snapshot": _PAGE,
    "back": _PAGE,
    "forward": _PAGE,
    "close_tab": {"tab"},
    "scroll": {"tab", "x", "y"},
    "screenshot": _PAGE | {"full_page"},
    "find": _PAGE | _QUERY,
    "wait": _PAGE | _TARGET,
    "click": _PAGE | _TARGET,
    "type": _PAGE | _TARGET | {"value"},
    "select": _PAGE | _TARGET | {"values"},
    "press": _PAGE | _TARGET | {"key"},
}
REQUIRED = {"open": "url", "new_tab": "url", "type": "value", "select": "values", "press": "key"}


def parse(action: str, inputs: JsonValue) -> Inputs:
    if action not in FIELDS:
        raise ValueError(f"unknown browser action: {action}")
    if not isinstance(inputs, dict) or inputs.keys() - FIELDS[action]:
        raise ValueError("supply only the fields offered for this action")
    if any(value is None for value in inputs.values()):
        raise ValueError("omit optional fields rather than supplying null")
    required = REQUIRED.get(action)
    if required is not None and required not in inputs:
        raise ValueError(f"{action} requires {required}")
    params = Inputs.model_validate(inputs)
    if "selector" in FIELDS[action]:
        if sum(bool(value) for value in (params.selector, params.role, params.ref)) > 1:
            raise ValueError("supply exactly one of selector, role or ref")
        if action != "wait" and not (params.selector or params.role or params.ref):
            raise ValueError("supply selector, role or ref")
        if params.name is not None and not params.role:
            raise ValueError("name requires role")
        if params.nth is not None and not (params.selector or params.role):
            raise ValueError("nth requires selector or role")
    return params


def schema(action: str) -> dict[str, JsonValue]:
    source = Inputs.model_json_schema()["properties"]
    properties: dict[str, JsonValue] = {}
    for name in sorted(FIELDS[action]):
        prop = dict(source[name])
        prop.pop("title", None)
        if "anyOf" in prop:
            prop = next(p for p in prop["anyOf"] if p.get("type") != "null")
        properties[name] = cast(JsonValue, prop)
    return {
        "type": "object",
        "properties": properties,
        "required": [REQUIRED[action]] if action in REQUIRED else [],
        "additionalProperties": False,
    }
