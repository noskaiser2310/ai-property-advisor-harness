import os
from pathlib import Path


QUERIES_DIR = Path(__file__).parent


def load_query(filename: str) -> str:
    filepath = QUERIES_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


GET_METRICS_SQL = load_query("get_metrics.sql")
GET_HISTORICAL_SQL = load_query("get_historical.sql")


def split_queries(sql_content: str) -> list[str]:
    return [q.strip() for q in sql_content.split(";") if q.strip()]


GET_METRICS_QUERIES = split_queries(GET_METRICS_SQL)
GET_HISTORICAL_QUERIES = split_queries(GET_HISTORICAL_SQL)