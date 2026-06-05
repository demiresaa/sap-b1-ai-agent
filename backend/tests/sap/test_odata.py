"""OData query builder testleri."""
from __future__ import annotations

from app.sap.odata import ODataQuery, and_, contains, eq, escape_literal, or_


def test_escape_literal_doubles_single_quotes() -> None:
    assert escape_literal("O'Brien") == "O''Brien"


def test_eq_quotes_strings() -> None:
    assert eq("CardCode", "C001") == "CardCode eq 'C001'"


def test_eq_numbers_not_quoted() -> None:
    assert eq("DocEntry", 42) == "DocEntry eq 42"


def test_eq_bool_literal() -> None:
    assert eq("Active", True) == "Active eq true"


def test_contains_escapes_quote() -> None:
    assert contains("CardName", "AB'C") == "contains(CardName,'AB''C')"


def test_and_filters_empty() -> None:
    assert and_("A", "", "B") == "A and B"


def test_or_wraps_expressions() -> None:
    assert or_("A", "B") == "(A) or (B)"


def test_query_builder_combines_all() -> None:
    q = (
        ODataQuery()
        .select("CardCode", "CardName")
        .filter(eq("CardType", "cCustomer"))
        .filter(contains("CardName", "Tekno"))
        .orderby("CardName", "asc")
        .top(10)
        .skip(20)
        .build()
    )
    assert q["$select"] == "CardCode,CardName"
    assert q["$filter"] == "CardType eq 'cCustomer' and contains(CardName,'Tekno')"
    assert q["$orderby"] == "CardName asc"
    assert q["$top"] == 10
    assert q["$skip"] == 20


def test_query_builder_handles_no_filter() -> None:
    q = ODataQuery().select("ItemCode").top(5).build()
    assert "$filter" not in q
    assert q["$top"] == 5
