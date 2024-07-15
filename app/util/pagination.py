"""Deduplicating default definitions for limit and offset query parameters."""

from fastapi import Query

limit_query_parameter = Query(100, description="Number of results to return")
offset_query_parameter = Query(0, description="Offset for pagination")
