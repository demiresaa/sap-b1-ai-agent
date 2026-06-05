"""OData v3/v4 query builder ve literal kaçış yardımcıları.

Service Layer OData literal'larında tek tırnak `''` ile kaçırılır. SQL benzeri
injection riskini önlemek için kullanıcı girdisi mutlaka bu modülden geçer.
"""
from __future__ import annotations

from typing import Any


def escape_literal(value: str) -> str:
    """OData string literal kaçışı: tek tırnak → çift tırnak."""
    return value.replace("'", "''")


def contains(field: str, value: str) -> str:
    """OData `contains(field,'value')` ifadesi üretir."""
    return f"contains({field},'{escape_literal(value)}')"


def eq(field: str, value: str | int | float | bool) -> str:
    """OData eşitlik filtresi (`field eq value`)."""
    if isinstance(value, bool):
        return f"{field} eq {'true' if value else 'false'}"
    if isinstance(value, (int, float)):
        return f"{field} eq {value}"
    return f"{field} eq '{escape_literal(str(value))}'"


def and_(*expressions: str) -> str:
    """Boş olmayan ifadeleri `and` ile birleştirir."""
    return " and ".join(e for e in expressions if e)


def or_(*expressions: str) -> str:
    return " or ".join(f"({e})" for e in expressions if e)


class ODataQuery:
    """OData parametre sözlüğü kurar.

    Örnek:
        ODataQuery()
            .select("CardCode", "CardName")
            .filter(eq("CardType", "cCustomer"))
            .top(50)
            .build()
        → {"$select": "CardCode,CardName", "$filter": "CardType eq 'cCustomer'", "$top": 50}
    """

    def __init__(self) -> None:
        self._params: dict[str, Any] = {}
        self._filters: list[str] = []

    def select(self, *fields: str) -> "ODataQuery":
        self._params["$select"] = ",".join(fields)
        return self

    def expand(self, *navigations: str) -> "ODataQuery":
        self._params["$expand"] = ",".join(navigations)
        return self

    def filter(self, expression: str) -> "ODataQuery":
        if expression:
            self._filters.append(expression)
        return self

    def orderby(self, field: str, direction: str = "asc") -> "ODataQuery":
        self._params["$orderby"] = f"{field} {direction}"
        return self

    def top(self, n: int) -> "ODataQuery":
        self._params["$top"] = n
        return self

    def skip(self, n: int) -> "ODataQuery":
        self._params["$skip"] = n
        return self

    def build(self) -> dict[str, Any]:
        params = dict(self._params)
        if self._filters:
            params["$filter"] = and_(*self._filters)
        return params
