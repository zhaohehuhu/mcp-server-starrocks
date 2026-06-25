# Copyright 2021-present StarRocks, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
from typing import Any, Optional


AUDIT_LOG_TABLE = "starrocks_audit_db__.starrocks_audit_tbl__"
SYSTEM_SCHEMAS = ("information_schema", "_statistics_", "sys")


def _sql_literal(value: Any) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _format_epoch_millis(value: int) -> str:
    return datetime.fromtimestamp(value / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")[:23]


def _bounded_limit(value: Optional[int], default: int = 20, maximum: int = 100) -> int:
    if value is None:
        return default
    return max(1, min(int(value), maximum))

def _display_number(value: Any) -> int | float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    if number.is_integer():
        return int(number)
    return round(number, 2)


class TableManagementTools:
    def __init__(self, db_client):
        self.db_client = db_client

    def get_top_hot_tables(
        self,
        db: Optional[str] = None,
        table: Optional[str] = None,
        min_start_time_ms: Optional[int] = None,
        max_start_time_ms: Optional[int] = None,
        top_n: int = 20,
    ) -> dict[str, Any]:
        """Get top hot tables."""
        limit = _bounded_limit(top_n)
        now = datetime.now()
        sql = self._build_top_hot_tables_sql(
            db=db,
            table=table,
            min_start_time_ms=min_start_time_ms,
            max_start_time_ms=max_start_time_ms,
            top_n=limit,
        )
        result = self.db_client.execute(sql)
        if not result.success:
            return {
                "success": False,
                "error": result.error_message or "Failed to get top hot tables.",
                "analysis_timestamp": now.isoformat(),
                "data_source": AUDIT_LOG_TABLE,
                "top_hot_tables": [],
            }

        column_names = result.column_names or []
        rows = result.rows or []
        top_tables = []
        for index, row in enumerate(rows[:limit]):
            item = dict(zip(column_names, row))
            top_tables.append(
                {
                    "rank": index + 1,
                    "db": item.get("table_schema"),
                    "table": item.get("table_name"),
                    "visit_count": _display_number(item.get("visit_count")),
                }
            )

        return {
            "success": True,
            "analysis_timestamp": now.isoformat(),
            "data_source": AUDIT_LOG_TABLE,
            "filters": {
                "db": db,
                "table": table,
                "min_start_time_ms": min_start_time_ms,
                "max_start_time_ms": max_start_time_ms,
                "top_n": limit,
            },
            "summary": {
                "top_n_requested": limit,
                "top_n_returned": len(top_tables),
                "execution_time": result.execution_time,
            },
            "top_hot_tables": top_tables,
        }


    @staticmethod
    def _build_top_hot_tables_sql(
        db: Optional[str],
        table: Optional[str],
        min_start_time_ms: Optional[int],
        max_start_time_ms: Optional[int],
        top_n: int,
    ) -> str:
        conditions = [
            "t.table_schema NOT IN ('information_schema', '_statistics_', 'sys')",
        ]
        if db:
            conditions.append(f"t.table_schema = {_sql_literal(db)}")
        if table:
            conditions.append(f"t.table_name LIKE {_sql_literal('%' + table + '%')}")
        if min_start_time_ms is not None and max_start_time_ms is not None:
            conditions.append(
                "a.`timestamp` BETWEEN "
                f"{_sql_literal(_format_epoch_millis(min_start_time_ms))} "
                f"AND {_sql_literal(_format_epoch_millis(max_start_time_ms))}"
            )

        where_sql = "\n AND ".join(conditions)
        return f"""
            SELECT
                t.table_name,
                t.table_schema,
                COUNT(a.`stmt`) AS visit_count
            FROM information_schema.tables t
            JOIN {AUDIT_LOG_TABLE} a
                ON a.`user` != 'root'
                AND LOWER(a.`stmt`) NOT LIKE '%show%'
                AND a.`stmt` LIKE CONCAT('%', t.table_name, '%')
            WHERE {where_sql}
            GROUP BY t.table_name, t.table_schema
            ORDER BY visit_count DESC
            LIMIT {top_n}
            """


def format_top_hot_tables_analysis(result: dict[str, Any]) -> str:
    """Format top hot table information."""
    if not result.get("success"):
        return f"Error getting top hot tables: {result.get('error', 'unknown error')}"

    summary = result.get("summary", {})
    lines = [
        "Top hot tables analysis completed.",
        (
            f"Returned {summary.get('top_n_returned', 0)} "
            f"of {summary.get('top_n_requested', 0)} requested table(s)."
        ),
    ]

    top_tables = result.get("top_hot_tables", [])
    if not top_tables:
        lines.append("No hot tables found for the specified criteria.")
        return "\n".join(lines)

    lines.append("Top tables:")
    for table in top_tables[:10]:
        lines.append(
            f"#{table.get('rank')} {table.get('db')}.{table.get('table')} "
            f"visits={table.get('visit_count')}"
        )

    return "\n".join(lines)
