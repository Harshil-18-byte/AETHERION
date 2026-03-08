"""
Data Validator — quality checks on the raw loaded data.
"""

from db.connection import get_connection


def validate_data() -> dict:
    """
    Run quality checks on options_raw and return a summary dict.
    Raises ValueError if critical checks fail.
    """
    conn = get_connection()
    issues = []

    # 1. Total row count
    total = conn.execute("SELECT COUNT(*) FROM options_raw").fetchone()[0]
    if total == 0:
        raise ValueError("options_raw is empty — no data loaded")

    # 2. Null checks in critical columns
    critical_cols = ["datetime", "strike", "expiry", "spot_close", "oi_CE", "oi_PE"]
    null_report = {}
    for col in critical_cols:
        null_count = conn.execute(
            f"SELECT COUNT(*) FROM options_raw WHERE {col} IS NULL"
        ).fetchone()[0]
        null_report[col] = null_count
        if null_count > 0:
            pct = round(null_count / total * 100, 2)
            issues.append(f"Column '{col}' has {null_count:,} NULLs ({pct}%)")

    # 3. Timestamp ordering — check for out-of-order timestamps
    disorder = conn.execute("""
        WITH ordered AS (
            SELECT datetime,
                   LAG(datetime) OVER (ORDER BY datetime) AS prev_dt
            FROM (SELECT DISTINCT datetime FROM options_raw) sub
        )
        SELECT COUNT(*) FROM ordered
        WHERE prev_dt IS NOT NULL AND datetime < prev_dt
    """).fetchone()[0]
    if disorder > 0:
        issues.append(f"Timestamp ordering: {disorder} out-of-order entries")

    # 4. Duplicate rows
    dup_count = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT datetime, strike, expiry, COUNT(*) AS cnt
            FROM options_raw
            GROUP BY datetime, strike, expiry
            HAVING cnt > 1
        )
    """).fetchone()[0]
    if dup_count > 0:
        issues.append(f"Duplicate (datetime, strike, expiry) combos: {dup_count:,}")

    # 5. Strike price range sanity
    strike_stats = conn.execute("""
        SELECT MIN(strike), MAX(strike), AVG(strike) FROM options_raw
    """).fetchone()
    min_strike, max_strike, avg_strike = strike_stats
    if min_strike <= 0:
        issues.append(f"Strike prices include non-positive values: min={min_strike}")
    if max_strike / min_strike > 10:
        issues.append(
            f"Wide strike range: {min_strike} – {max_strike} (ratio {max_strike/min_strike:.1f}x)"
        )

    # 6. Date range and expiry sanity
    date_range = conn.execute("""
        SELECT MIN(datetime), MAX(datetime),
               COUNT(DISTINCT expiry) AS n_expiries,
               COUNT(DISTINCT CAST(datetime AS DATE)) AS n_dates
        FROM options_raw
    """).fetchone()

    # 7. Spot price sanity
    spot_stats = conn.execute("""
        SELECT MIN(spot_close), MAX(spot_close), AVG(spot_close)
        FROM options_raw
        WHERE spot_close IS NOT NULL
    """).fetchone()

    summary = {
        "total_rows": total,
        "null_report": null_report,
        "timestamp_range": {
            "start": str(date_range[0]),
            "end": str(date_range[1]),
        },
        "n_expiries": date_range[2],
        "n_trading_dates": date_range[3],
        "strike_range": {"min": float(min_strike), "max": float(max_strike)},
        "spot_range": {
            "min": float(spot_stats[0]),
            "max": float(spot_stats[1]),
            "avg": round(float(spot_stats[2]), 2),
        },
        "issues": issues,
        "status": "PASS" if len(issues) == 0 else "WARN",
    }

    # Print summary
    print(f"\n{'═' * 60}")
    print(f"  DATA QUALITY REPORT")
    print(f"{'═' * 60}")
    print(f"  Total rows:       {total:,}")
    print(f"  Date range:       {date_range[0]}  →  {date_range[1]}")
    print(f"  Expiries:         {date_range[2]}")
    print(f"  Trading dates:    {date_range[3]}")
    print(f"  Strike range:     {min_strike:,.0f} – {max_strike:,.0f}")
    print(f"  Spot range:       {spot_stats[0]:,.2f} – {spot_stats[1]:,.2f}")
    if issues:
        print(f"\n  ⚠ Issues ({len(issues)}):")
        for iss in issues:
            print(f"    - {iss}")
    else:
        print(f"\n  ✅ All checks passed")
    print(f"{'═' * 60}\n")

    return summary
