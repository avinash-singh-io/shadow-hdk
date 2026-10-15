"""Optional read components use the same host mechanisms under the ordinary act pipeline."""

from pydantic import JsonValue

from shadow_hdk.adapters.workbench.host import HostDoor
from shadow_hdk.kernel import Component, Interface, Observation, Provenance, Refused, Registration
from shadow_hdk.runtime.environment import effects_of


class WorkbenchComponents:
    def __init__(self, door: HostDoor) -> None:
        self._door = door

    async def registrations(self) -> list[Registration]:
        shapes: dict[str, dict[str, JsonValue]] = {
            "list_jobs": {},
            "read_job": {
                "job": {"type": "string"},
                "cursor": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 1000000},
            },
            "test_results": {"path": {"type": "string"}},
        }
        environment = self._door.environment
        return [
            Registration(
                name,
                Component(
                    Interface(
                        name,
                        f"{name.replace('_', ' ')} in the owned working copy.",
                        {
                            "type": "object",
                            "properties": properties,
                            "required": ["job"]
                            if name == "read_job"
                            else ["path"]
                            if name == "test_results"
                            else [],
                            "additionalProperties": False,
                        },
                        {"type": "object"},
                    ),
                    effects=effects_of(environment.isolation, environment.mode, "read"),
                    provenance=Provenance("host", "workbench", ""),
                ),
            )
            for name, properties in shapes.items()
        ]

    async def invoke(self, registration: str, inputs: JsonValue) -> Observation:
        if not isinstance(inputs, dict):
            return Refused("workbench inputs must be an object")
        if registration == "list_jobs" and not inputs:
            return await self._door.jobs()
        if registration == "read_job" and isinstance(inputs.get("job"), str):
            cursor, limit = inputs.get("cursor", 0), inputs.get("limit", 64000)
            if (
                isinstance(cursor, int)
                and isinstance(limit, int)
                and not inputs.keys() - {"job", "cursor", "limit"}
            ):
                return await self._door.output(str(inputs["job"]), cursor=cursor, limit=limit)
        if (
            registration == "test_results"
            and isinstance(inputs.get("path"), str)
            and inputs.keys() == {"path"}
        ):
            return await self._door.results(str(inputs["path"]))
        return Refused("unknown workbench component or invalid inputs")
