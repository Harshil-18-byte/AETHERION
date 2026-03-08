"""
Pattern Detection — volatility smile/skew, support/resistance, activity scoring.
"""

import numpy as np
import pandas as pd
from db.connection import get_connection


def run_pattern_detection() -> dict:
    """
    Detect structural patterns in the options data:
      1. Volatility smile / skew per expiry
      2. Support / resistance levels from OI concentration
      3. Unusual activity scoring
    Returns a dict with all detected patterns.
    """
    conn = get_connection()

    # ═══════════════════════════════════════════════════════════════
    # 1. VOLATILITY SMILE / SKEW DETECTION
    #    For each expiry, look at IV vs moneyness:
    #    - Smile:  both OTM calls and OTM puts have higher IV than ATM
    #    - Skew:   one side has higher IV than the other
    #    - Flat:   IV is roughly uniform
    # ═══════════════════════════════════════════════════════════════
    smile_data = conn.execute("""
        WITH latest AS (
            SELECT expiry, MAX(datetime) AS max_dt
            FROM options_enriched GROUP BY expiry
        ),
        snapshot AS (
            SELECT e.strike, e.expiry, e.iv_proxy, e.moneyness, e.spot_close
            FROM options_enriched e
            JOIN latest l ON e.expiry = l.expiry AND e.datetime = l.max_dt
            WHERE e.iv_proxy IS NOT NULL AND e.iv_proxy > 0
        ),
        bucketed AS (
            SELECT
                expiry,
                CASE
                    WHEN moneyness < 0.95 THEN 'DEEP_OTM_PE'
                    WHEN moneyness < 0.99 THEN 'OTM_PE'
                    WHEN moneyness <= 1.01 THEN 'ATM'
                    WHEN moneyness <= 1.05 THEN 'OTM_CE'
                    ELSE 'DEEP_OTM_CE'
                END AS bucket,
                AVG(iv_proxy) AS avg_iv,
                COUNT(*) AS n_strikes
            FROM snapshot
            GROUP BY expiry, bucket
        )
        SELECT * FROM bucketed ORDER BY expiry, bucket
    """).df()

    smile_results = []
    for exp in smile_data["expiry"].unique():
        exp_data = smile_data[smile_data["expiry"] == exp]
        bucket_iv = dict(zip(exp_data["bucket"], exp_data["avg_iv"]))

        atm_iv = bucket_iv.get("ATM", 0)
        otm_pe = bucket_iv.get("OTM_PE", atm_iv)
        otm_ce = bucket_iv.get("OTM_CE", atm_iv)
        deep_pe = bucket_iv.get("DEEP_OTM_PE", otm_pe)
        deep_ce = bucket_iv.get("DEEP_OTM_CE", otm_ce)

        if atm_iv > 0:
            put_skew = (otm_pe - atm_iv) / atm_iv
            call_skew = (otm_ce - atm_iv) / atm_iv
        else:
            put_skew = call_skew = 0

        # Classification
        if put_skew > 0.05 and call_skew > 0.05:
            pattern = "SMILE"
        elif put_skew > 0.05 and call_skew < -0.02:
            pattern = "PUT_SKEW"
        elif call_skew > 0.05 and put_skew < -0.02:
            pattern = "CALL_SKEW"
        elif put_skew > 0.05:
            pattern = "MILD_PUT_SKEW"
        elif call_skew > 0.05:
            pattern = "MILD_CALL_SKEW"
        else:
            pattern = "FLAT"

        smile_results.append({
            "expiry": str(exp)[:10],
            "pattern": pattern,
            "atm_iv": round(float(atm_iv), 4),
            "otm_put_iv": round(float(otm_pe), 4),
            "otm_call_iv": round(float(otm_ce), 4),
            "put_skew_pct": round(float(put_skew * 100), 2),
            "call_skew_pct": round(float(call_skew * 100), 2),
        })

    # ═══════════════════════════════════════════════════════════════
    # 2. SUPPORT / RESISTANCE from OI concentration
    #    Strikes with highest OI = potential support (put-heavy)
    #    or resistance (call-heavy)
    # ═══════════════════════════════════════════════════════════════
    sr_levels = conn.execute("""
        WITH latest AS (
            SELECT expiry, MAX(datetime) AS max_dt
            FROM options_enriched GROUP BY expiry
        ),
        snapshot AS (
            SELECT e.strike, e.expiry, e.oi_CE, e.oi_PE, e.spot_close,
                   e.total_oi
            FROM options_enriched e
            JOIN latest l ON e.expiry = l.expiry AND e.datetime = l.max_dt
        ),
        ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY expiry ORDER BY oi_CE DESC) AS ce_rank,
                   ROW_NUMBER() OVER (PARTITION BY expiry ORDER BY oi_PE DESC) AS pe_rank
            FROM snapshot
        )
        SELECT strike, expiry, oi_CE, oi_PE, total_oi, spot_close,
               ce_rank, pe_rank
        FROM ranked
        WHERE ce_rank <= 5 OR pe_rank <= 5
        ORDER BY expiry, strike
    """).df()

    support_resistance = []
    for exp in sr_levels["expiry"].unique():
        exp_data = sr_levels[sr_levels["expiry"] == exp]
        spot = exp_data["spot_close"].iloc[0]

        # Top call OI = resistance levels
        top_calls = exp_data.nsmallest(3, "ce_rank")[["strike", "oi_CE"]].to_dict("records")
        # Top put OI = support levels
        top_puts = exp_data.nsmallest(3, "pe_rank")[["strike", "oi_PE"]].to_dict("records")

        resistance = [{"strike": float(r["strike"]), "oi": int(r["oi_CE"])} for r in top_calls]
        support = [{"strike": float(r["strike"]), "oi": int(r["oi_PE"])} for r in top_puts]

        support_resistance.append({
            "expiry": str(exp)[:10],
            "spot": round(float(spot), 2),
            "resistance_levels": resistance,
            "support_levels": support,
        })

    # ═══════════════════════════════════════════════════════════════
    # 3. MAX PAIN per expiry (computed inline to avoid MV dependency)
    # ═══════════════════════════════════════════════════════════════
    max_pain = conn.execute("""
        WITH latest AS (
            SELECT expiry, MAX(datetime) AS max_dt
            FROM options_enriched
            GROUP BY expiry
        ),
        chain AS (
            SELECT e.strike, e.expiry, e.oi_CE, e.oi_PE
            FROM options_enriched e
            JOIN latest l ON e.expiry = l.expiry AND e.datetime = l.max_dt
        ),
        all_strikes AS (
            SELECT DISTINCT strike AS settlement FROM chain
        ),
        liabilities AS (
            SELECT
                c.expiry,
                s.settlement AS settlement_price,
                SUM(
                    CASE WHEN s.settlement > c.strike
                         THEN (s.settlement - c.strike) * c.oi_CE
                         ELSE 0 END
                ) + SUM(
                    CASE WHEN s.settlement < c.strike
                         THEN (c.strike - s.settlement) * c.oi_PE
                         ELSE 0 END
                ) AS total_liability
            FROM chain c
            CROSS JOIN all_strikes s
            GROUP BY c.expiry, s.settlement
        ),
        min_liability AS (
            SELECT expiry,
                   FIRST(settlement_price ORDER BY total_liability ASC) AS max_pain_strike,
                   MIN(total_liability) AS min_total_liability
            FROM liabilities
            GROUP BY expiry
        )
        SELECT * FROM min_liability ORDER BY expiry
    """).df()

    max_pain_list = []
    for _, row in max_pain.iterrows():
        max_pain_list.append({
            "expiry": str(row["expiry"])[:10],
            "max_pain_strike": float(row["max_pain_strike"]),
            "total_liability": round(float(row["min_total_liability"]), 0),
        })

    summary = {
        "smile_skew": smile_results,
        "support_resistance": support_resistance,
        "max_pain": max_pain_list,
    }

    print(f"[PATTERNS] Detected: {len(smile_results)} smile/skew, "
          f"{len(support_resistance)} S/R levels, "
          f"{len(max_pain_list)} max-pain points ✅")

    return summary
