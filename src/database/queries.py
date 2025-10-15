# src/database/queries.py
"""Common query patterns."""

import duckdb
from typing import Dict, Any


def get_fire_statistics(conn: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    """Get summary statistics about fires."""

    result = conn.execute("""
        SELECT
            COUNT(*) as total_fires,
            COUNT(DISTINCT acq_date) as days_with_fires,
            AVG(risk_score) as avg_risk_score,
            MAX(risk_score) as max_risk_score,
            COUNT(CASE WHEN risk_category = 'High' THEN 1 END) as high_risk_count,
            COUNT(CASE WHEN risk_category = 'Moderate' THEN 1 END) as moderate_risk_count,
            COUNT(CASE WHEN risk_category = 'Low' THEN 1 END) as low_risk_count
        FROM fires
    """).fetchone()

    if result is None:
        return {
            "total_fires": 0,
            "days_with_fires": 0,
            "avg_risk_score": 0.0,
            "max_risk_score": 0.0,
            "high_risk_count": 0,
            "moderate_risk_count": 0,
            "low_risk_count": 0,
        }

    return {
        "total_fires": result[0],
        "days_with_fires": result[1],
        "avg_risk_score": round(result[2], 2) if result[2] else 0,
        "max_risk_score": round(result[3], 2) if result[3] else 0,
        "high_risk_count": result[4],
        "moderate_risk_count": result[5],
        "low_risk_count": result[6],
    }
