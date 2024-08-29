"""Deduplicating default definitions for limit and offset query parameters."""

from fastapi import Query

limit_query_parameter = Query(
    1000, description="Number of results to return", ge=0, le=10000
)
offset_query_parameter = Query(0, description="Offset for pagination", ge=0)
order_by_query_parameter = Query(
    "id", description="The column to order by", include_in_schema=False
)
descending_query_parameter = Query(
    True,
    description=(
        "Whether to return results in descending order. "
        "Results are ordered by record created time."
    ),
)
