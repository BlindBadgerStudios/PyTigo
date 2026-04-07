from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from .models import (
    TigoAlert,
    TigoAuth,
    TigoCSVTable,
    TigoObjectNode,
    TigoPage,
    TigoSource,
    TigoSummary,
    TigoSystem,
    TigoSystemLayout,
)


@runtime_checkable
class TigoClientProtocol(Protocol):
    """
    Structural protocol satisfied by both TigoClient (cloud) and TigoCCAClient (local).

    Code that consumes a Tigo client — such as Prom_Tigo's TigoCollector — should
    type-hint against this rather than a concrete class so that either backend can
    be injected without changes to the consumer.

    Python's structural subtyping means neither concrete class needs to explicitly
    inherit from this; they just need to implement the listed methods with compatible
    signatures.
    """

    def login(self) -> TigoAuth: ...

    def list_systems(
        self,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort: str | None = None,
    ) -> TigoPage[TigoSystem]: ...

    def get_system(
        self,
        system_id: int,
        *,
        include: list[str] | None = None,
    ) -> TigoSystem: ...

    def get_layout(self, system_id: int) -> TigoSystemLayout: ...

    def get_objects(self, system_id: int) -> list[TigoObjectNode]: ...

    def get_sources(self, system_id: int) -> list[TigoSource]: ...

    def get_summary(self, system_id: int) -> TigoSummary: ...

    def get_aggregate(
        self,
        system_id: int,
        *,
        start: str,
        end: str,
        level: Literal["min", "hour", "day"] = "min",
        param: str = "Pin",
        object_ids: list[int] | None = None,
        header: str | None = None,
    ) -> TigoCSVTable: ...

    def get_alerts(
        self,
        system_id: int,
        *,
        language: str | None = None,
        start_added: str | None = None,
        end_added: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> TigoPage[TigoAlert]: ...
