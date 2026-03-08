/**
 * Analytics Engine — Core quantitative analysis for options market data.
 * Pure TypeScript implementation — no backend required.
 *
 * Features:
 * 1. Gamma Exposure (GEX) Analysis
 * 2. Gamma Flip Level Detection
 * 3. Options Flow Pressure Indicator
 * 4. Volatility Regime Detection
 * 5. Liquidity Cluster Detection
 * 6. Unusual Options Activity Detection
 * 7. Market Structure Analyzer
 * 8. Market Stability Score
 * 9. Market Narrative Generator
 * 10. Market Event Timeline
 */

import type {
  OptionRow, GEXResult, GEXByStrike, GammaFlipResult,
  FlowPressureResult, VolRegimeResult, LiquidityResult,
  UnusualActivityResult, MarketStructureResult, StabilityResult,
  TimelineEvent, FullAnalysis, IVByStrike, LiquidityItem,
} from "./types";

import {
  computeDeltaExposure, computeVannaCharm, computeSurface3D, computeSqueezeMetrics,
  simulateLiveTape, simulateDarkPool, computeRetailInst, detectAlgoClusters, computeTradeSide,
  computeTermStructure, computeVolCones, computeSkewIndex, computeExpectedMove, computeEarningsCrush,
  computeMaxPain, computeVolumeProfile, computeSyntheticArb, computeSectorCorrelation
} from "./advancedAnalytics";

const CONTRACT_SIZE = 25; // NIFTY lot size

// ─── Helpers ─────────────────────────────────────────────────────────────────

function normalPdf(x: number): number {
  return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
}

function approximateIV(optionPrice: number, spot: number): number {
  if (spot <= 0 || optionPrice <= 0) return 0;
  const iv = (optionPrice * Math.sqrt(2 * Math.PI)) / spot;
  return Math.round(iv * 100 * 100) / 100;
}

function approximateGamma(spot: number, strike: number, ivPct: number, tteYears = 7 / 365): number {
  if (ivPct <= 0 || spot <= 0 || tteYears <= 0) return 0;
  const sigma = ivPct / 100;
  const d1Num = Math.log(spot / strike) + 0.5 * sigma * sigma * tteYears;
  const d1Den = sigma * Math.sqrt(tteYears);
  if (d1Den === 0) return 0;
  const d1 = d1Num / d1Den;
  return normalPdf(d1) / (spot * sigma * Math.sqrt(tteYears));
}

function percentile(arr: number[], p: number): number {
  const sorted = [...arr].sort((a, b) => a - b);
  const idx = (p / 100) * (sorted.length - 1);
  const lower = Math.floor(idx);
  const upper = Math.ceil(idx);
  if (lower === upper) return sorted[lower];
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (idx - lower);
}

function mean(arr: number[]): number {
  return arr.length === 0 ? 0 : arr.reduce((a, b) => a + b, 0) / arr.length;
}

function std(arr: number[]): number {
  if (arr.length < 2) return 0;
  const m = mean(arr);
  const variance = arr.reduce((sum, v) => sum + (v - m) ** 2, 0) / arr.length;
  return Math.sqrt(variance);
}

// ─── Feature 1: Gamma Exposure (GEX) ────────────────────────────────────────

export function computeGEX(snapshot: OptionRow[]): GEXResult {
  const spot = snapshot.length > 0 ? snapshot[snapshot.length - 1].spot_close : 0;
  const byStrike: GEXByStrike[] = [];

  for (const row of snapshot) {
    const s = row.spot_close || spot;
    const ivCe = approximateIV(row.CE || 0, s);
    const ivPe = approximateIV(row.PE || 0, s);
    const gammaCe = approximateGamma(s, row.strike, ivCe);
    const gammaPe = approximateGamma(s, row.strike, ivPe);

    const gexCe = (gammaCe * row.oi_CE * CONTRACT_SIZE * s) / 1e7;
    const gexPe = -(gammaPe * row.oi_PE * CONTRACT_SIZE * s) / 1e7;

    byStrike.push({
      strike: row.strike,
      call_gex: Math.round(gexCe * 10000) / 10000,
      put_gex: Math.round(gexPe * 10000) / 10000,
      net_gex: Math.round((gexCe + gexPe) * 10000) / 10000,
      iv_ce: ivCe, iv_pe: ivPe,
    });
  }

  const totalGex = byStrike.reduce((sum, s) => sum + s.net_gex, 0);

  return {
    by_strike: byStrike,
    total_gex: Math.round(totalGex * 10000) / 10000,
    spot,
    interpretation: totalGex > 0
      ? "Market Stabilizing (Positive Gamma)"
      : "Market Volatile (Negative Gamma)",
  };
}

// ─── Feature 2: Gamma Flip Level ─────────────────────────────────────────────

export function detectGammaFlip(gexData: GEXResult): GammaFlipResult {
  const sorted = [...gexData.by_strike].sort((a, b) => a.strike - b.strike);
  let cumulative = 0;
  let prevSign: number | null = null;
  let flipLevel: number | null = null;
  const cumData: { strike: number; cumulative_gex: number }[] = [];

  for (const item of sorted) {
    cumulative += item.net_gex;
    const currentSign = cumulative >= 0 ? 1 : -1;
    cumData.push({ strike: item.strike, cumulative_gex: Math.round(cumulative * 10000) / 10000 });
    if (prevSign !== null && currentSign !== prevSign) {
      flipLevel = item.strike;
    }
    prevSign = currentSign;
  }

  return { gamma_flip_level: flipLevel, cumulative_gex: cumData };
}

// ─── Feature 3: Flow Pressure ────────────────────────────────────────────────

export function computeFlowPressure(snapshot: OptionRow[]): FlowPressureResult {
  let totalCallVol = 0, totalPutVol = 0;
  const byStrike: FlowPressureResult["by_strike"] = [];

  for (const row of snapshot) {
    totalCallVol += row.volume_CE;
    totalPutVol += row.volume_PE;
    const tv = row.volume_CE + row.volume_PE;
    byStrike.push({
      strike: row.strike,
      call_volume: row.volume_CE,
      put_volume: row.volume_PE,
      strike_pressure: tv > 0 ? Math.round(((row.volume_CE - row.volume_PE) / tv) * 10000) / 10000 : 0,
    });
  }

  const totalVol = totalCallVol + totalPutVol;
  const pressure = totalVol > 0 ? (totalCallVol - totalPutVol) / totalVol : 0;

  let sentiment: string;
  if (pressure > 0.3) sentiment = "Strong Bullish Flow";
  else if (pressure > 0.1) sentiment = "Mildly Bullish Flow";
  else if (pressure < -0.3) sentiment = "Strong Bearish Flow";
  else if (pressure < -0.1) sentiment = "Mildly Bearish Flow";
  else sentiment = "Neutral Flow";

  return {
    flow_pressure: Math.round(pressure * 10000) / 10000,
    sentiment,
    total_call_volume: totalCallVol,
    total_put_volume: totalPutVol,
    by_strike: byStrike,
  };
}

// ─── Feature 4: Volatility Regime ────────────────────────────────────────────

export function detectVolRegime(snapshot: OptionRow[]): VolRegimeResult {
  const spot = snapshot.length > 0 ? snapshot[snapshot.length - 1].spot_close : 0;
  const ivByStrike: IVByStrike[] = [];

  for (const row of snapshot) {
    const s = row.spot_close || spot;
    const iv = approximateIV(row.CE || 0, s);
    ivByStrike.push({ strike: row.strike, iv });
  }

  const ivValues = ivByStrike.map(x => x.iv).filter(v => v > 0);
  if (ivValues.length < 3) {
    return { regime: "Insufficient Data", mean_iv: 0, std_iv: 0, cv: 0, atm_iv: 0, iv_by_strike: ivByStrike };
  }

  const meanIV = mean(ivValues);
  const stdIV = std(ivValues);
  const cv = meanIV > 0 ? stdIV / meanIV : 0;

  const atmRange = spot * 0.02;
  const atmIvs = ivByStrike.filter(x => Math.abs(x.strike - spot) <= atmRange && x.iv > 0).map(x => x.iv);
  const atmMean = atmIvs.length > 0 ? mean(atmIvs) : meanIV;

  let regime: string;
  if (cv > 0.35) regime = "Expansion";
  else if (cv < 0.15) regime = "Compression";
  else regime = "Stable";

  return {
    regime,
    mean_iv: Math.round(meanIV * 100) / 100,
    std_iv: Math.round(stdIV * 100) / 100,
    cv: Math.round(cv * 10000) / 10000,
    atm_iv: Math.round(atmMean * 100) / 100,
    iv_by_strike: ivByStrike,
  };
}

// ─── Feature 5: Liquidity Clusters ───────────────────────────────────────────

export function detectLiquidityClusters(snapshot: OptionRow[]): LiquidityResult {
  const data: LiquidityItem[] = snapshot.map(row => ({
    strike: row.strike,
    total_oi: row.oi_CE + row.oi_PE,
    total_volume: row.volume_CE + row.volume_PE,
    call_oi: row.oi_CE,
    put_oi: row.oi_PE,
    liquidity_score: 0,
  }));

  if (data.length === 0) return { clusters: [], liquidity_map: [], threshold: 0 };

  const maxOI = Math.max(...data.map(d => d.total_oi)) || 1;
  const maxVol = Math.max(...data.map(d => d.total_volume)) || 1;

  for (const d of data) {
    d.liquidity_score = Math.round((0.6 * (d.total_oi / maxOI) + 0.4 * (d.total_volume / maxVol)) * 10000) / 10000;
  }

  const scores = data.map(d => d.liquidity_score);
  const threshold = percentile(scores, 70);
  const clusters = data.filter(d => d.liquidity_score >= threshold).sort((a, b) => b.liquidity_score - a.liquidity_score);

  return {
    clusters,
    liquidity_map: [...data].sort((a, b) => a.strike - b.strike),
    threshold: Math.round(threshold * 10000) / 10000,
  };
}

// ─── Feature 6: Unusual Activity Detection ───────────────────────────────────

export function detectUnusualActivity(snapshot: OptionRow[]): UnusualActivityResult {
  const totalVols = snapshot.map(r => r.volume_CE + r.volume_PE);
  if (totalVols.length < 3) return { alerts: [], has_unusual_activity: false, mean_volume: 0, std_volume: 0 };

  const m = mean(totalVols);
  const s = std(totalVols);
  if (s === 0) return { alerts: [], has_unusual_activity: false, mean_volume: m, std_volume: 0 };

  const alerts: UnusualActivityResult["alerts"] = [];
  for (const row of snapshot) {
    const tv = row.volume_CE + row.volume_PE;
    const z = (tv - m) / s;
    if (Math.abs(z) > 2.0) {
      alerts.push({
        strike: row.strike,
        total_volume: tv,
        call_volume: row.volume_CE,
        put_volume: row.volume_PE,
        z_score: Math.round(z * 100) / 100,
        pct_above_mean: m > 0 ? Math.round(((tv - m) / m) * 1000) / 10 : 0,
        type: row.volume_CE > row.volume_PE * 1.5 ? "Call Heavy" : row.volume_PE > row.volume_CE * 1.5 ? "Put Heavy" : "Mixed",
      });
    }
  }

  alerts.sort((a, b) => Math.abs(b.z_score) - Math.abs(a.z_score));

  return {
    alerts: alerts.slice(0, 10),
    has_unusual_activity: alerts.length > 0,
    mean_volume: Math.round(m),
    std_volume: Math.round(s),
  };
}

// ─── Feature 7: Market Structure ─────────────────────────────────────────────

export function analyzeMarketStructure(snapshot: OptionRow[]): MarketStructureResult {
  if (snapshot.length === 0) {
    return { support: 0, support_oi: 0, resistance: 0, resistance_oi: 0, spot: 0, pcr: 0, range: "" };
  }

  let maxPutOI = 0, maxCallOI = 0, supportStrike = 0, resistanceStrike = 0;
  let totalPutOI = 0, totalCallOI = 0;

  for (const row of snapshot) {
    totalPutOI += row.oi_PE;
    totalCallOI += row.oi_CE;
    if (row.oi_PE > maxPutOI) { maxPutOI = row.oi_PE; supportStrike = row.strike; }
    if (row.oi_CE > maxCallOI) { maxCallOI = row.oi_CE; resistanceStrike = row.strike; }
  }

  const spot = snapshot[snapshot.length - 1].spot_close;
  const pcr = totalCallOI > 0 ? totalPutOI / totalCallOI : 0;

  return {
    support: supportStrike,
    support_oi: maxPutOI,
    resistance: resistanceStrike,
    resistance_oi: maxCallOI,
    spot,
    pcr: Math.round(pcr * 10000) / 10000,
    range: `${supportStrike} — ${resistanceStrike}`,
  };
}

// ─── Feature 8: Market Stability Score ───────────────────────────────────────

export function computeStabilityScore(
  snapshot: OptionRow[], gex: GEXResult, flow: FlowPressureResult,
  vol: VolRegimeResult, unusual: UnusualActivityResult
): StabilityResult {
  const gexScore = Math.min(Math.max(50 + gex.total_gex * 5, 0), 100);
  const flowScore = Math.max(100 - Math.abs(flow.flow_pressure) * 200, 0);

  let volScore: number;
  if (vol.regime === "Compression") volScore = 85;
  else if (vol.regime === "Stable") volScore = 70;
  else if (vol.regime === "Expansion") volScore = 30;
  else volScore = 50;

  const anomalyScore = Math.max(100 - unusual.alerts.length * 15, 0);

  const totalCallOI = snapshot.reduce((s, r) => s + r.oi_CE, 0);
  const totalPutOI = snapshot.reduce((s, r) => s + r.oi_PE, 0);
  const totalOI = totalCallOI + totalPutOI;
  const oiScore = totalOI > 0 ? Math.max(100 - (Math.abs(totalCallOI - totalPutOI) / totalOI) * 200, 0) : 50;

  const composite = Math.round(Math.min(Math.max(
    gexScore * 0.30 + flowScore * 0.20 + volScore * 0.25 + anomalyScore * 0.15 + oiScore * 0.10,
    0), 100) * 10) / 10;

  let status: string;
  if (composite >= 75) status = "Highly Stable";
  else if (composite >= 55) status = "Moderately Stable";
  else if (composite >= 35) status = "Moderately Unstable";
  else status = "Highly Unstable";

  return {
    score: composite,
    status,
    components: {
      gamma_exposure: Math.round(gexScore * 10) / 10,
      flow_balance: Math.round(flowScore * 10) / 10,
      volatility: volScore,
      anomaly: anomalyScore,
      oi_balance: Math.round(oiScore * 10) / 10,
    },
  };
}

// ─── Feature 9: Narrative Generator ──────────────────────────────────────────

export function generateNarrative(
  structure: MarketStructureResult, gex: GEXResult, flow: FlowPressureResult,
  vol: VolRegimeResult, stability: StabilityResult, unusual: UnusualActivityResult
): string {
  const parts: string[] = [];

  if (flow.sentiment.includes("Bullish"))
    parts.push("The options market currently shows bullish sentiment.");
  else if (flow.sentiment.includes("Bearish"))
    parts.push("The options market currently shows bearish sentiment.");
  else parts.push("The options market currently shows neutral sentiment.");

  if (structure.support && structure.resistance) {
    parts.push(
      `Put open interest concentration near ${structure.support} suggests strong support, ` +
      `while call open interest buildup near ${structure.resistance} indicates resistance.`
    );
  }

  if (structure.pcr > 1.2)
    parts.push(`The put-call ratio of ${structure.pcr.toFixed(2)} signals elevated hedging demand.`);
  else if (structure.pcr < 0.8)
    parts.push(`The put-call ratio of ${structure.pcr.toFixed(2)} signals elevated speculative call interest.`);

  parts.push(gex.total_gex > 0
    ? "Positive net gamma exposure suggests dealers will dampen volatility through hedging."
    : "Negative net gamma exposure suggests dealers may amplify moves through hedging activity.");

  parts.push(`Volatility is in ${vol.regime.toLowerCase()} mode with ATM implied volatility at ${vol.atm_iv.toFixed(1)}%.`);
  parts.push(`Overall market stability score is ${stability.score.toFixed(0)}/100 (${stability.status}).`);

  if (unusual.has_unusual_activity)
    parts.push(`${unusual.alerts.length} unusual activity alert(s) detected — monitor closely.`);

  return parts.join(" ");
}

// ─── Feature 10: Event Timeline ──────────────────────────────────────────────

export function generateTimeline(timeSeries: OptionRow[]): TimelineEvent[] {
  if (timeSeries.length === 0) return [];

  const events: TimelineEvent[] = [];
  const grouped = new Map<string, OptionRow[]>();

  for (const row of timeSeries) {
    const ts = row.datetime;
    if (!grouped.has(ts)) grouped.set(ts, []);
    grouped.get(ts)!.push(row);
  }

  const timestamps = [...grouped.keys()].sort();
  let prevCallVol = 0, prevPutVol = 0, prevCallOI = 0, prevPutOI = 0;

  for (let i = 0; i < timestamps.length; i++) {
    const ts = timestamps[i];
    const rows = grouped.get(ts)!;
    const callVol = rows.reduce((s, r) => s + r.volume_CE, 0);
    const putVol = rows.reduce((s, r) => s + r.volume_PE, 0);
    const callOI = rows.reduce((s, r) => s + r.oi_CE, 0);
    const putOI = rows.reduce((s, r) => s + r.oi_PE, 0);

    const tsShort = ts.includes(" ") ? ts.split(" ")[1]?.slice(0, 5) || ts : ts;

    if (i > 0) {
      if (prevCallVol > 0 && callVol > prevCallVol * 2)
        events.push({ time: tsShort, event: "Call volume spike detected", severity: "high" });
      if (prevPutVol > 0 && putVol > prevPutVol * 2)
        events.push({ time: tsShort, event: "Put volume spike detected", severity: "high" });
      if (prevPutOI > 0 && (putOI - prevPutOI) / prevPutOI > 0.05)
        events.push({ time: tsShort, event: "Put OI buildup detected", severity: "medium" });
      if (prevCallOI > 0 && (callOI - prevCallOI) / prevCallOI > 0.05)
        events.push({ time: tsShort, event: "Call OI buildup detected", severity: "medium" });
    }

    prevCallVol = callVol; prevPutVol = putVol; prevCallOI = callOI; prevPutOI = putOI;
  }

  // Deduplicate consecutive identical events
  const deduped: TimelineEvent[] = [];
  for (const e of events) {
    if (!deduped.length || deduped[deduped.length - 1].event !== e.event || deduped[deduped.length - 1].time !== e.time)
      deduped.push(e);
  }

  return deduped.slice(-20);
}

// ─── Master Runner ───────────────────────────────────────────────────────────

export function runFullAnalysis(snapshot: OptionRow[], timeSeries: OptionRow[]): FullAnalysis {
  const gex = computeGEX(snapshot);
  const gamma_flip = detectGammaFlip(gex);
  const flow_pressure = computeFlowPressure(snapshot);
  const vol_regime = detectVolRegime(snapshot);
  const liquidity = detectLiquidityClusters(snapshot);
  const unusual_activity = detectUnusualActivity(snapshot);
  const market_structure = analyzeMarketStructure(snapshot);
  const stability = computeStabilityScore(snapshot, gex, flow_pressure, vol_regime, unusual_activity);
  const narrative = generateNarrative(market_structure, gex, flow_pressure, vol_regime, stability, unusual_activity);
  const timeline = generateTimeline(timeSeries);
  
  // Advanced Features Extensions
  const delta_exposure = computeDeltaExposure(snapshot);
  const vanna_charm = computeVannaCharm(snapshot);
  const surface_3d = computeSurface3D(snapshot);
  const squeeze_metrics = computeSqueezeMetrics(snapshot);
  
  const live_tape = simulateLiveTape(snapshot);
  const dark_pool = simulateDarkPool(snapshot);
  const retail_inst = computeRetailInst(snapshot);
  const algo_clusters = detectAlgoClusters(snapshot);
  const trade_side = computeTradeSide(snapshot);
  
  const term_structure = computeTermStructure(snapshot);
  const vol_cones = computeVolCones(snapshot);
  const skew_index = computeSkewIndex(snapshot);
  const expected_move = computeExpectedMove(snapshot);
  const earnings_crush = computeEarningsCrush();
  
  const max_pain = computeMaxPain(snapshot);
  const volume_profile = computeVolumeProfile(snapshot);
  const synthetic_arb = computeSyntheticArb(snapshot);
  const sector_correlation = computeSectorCorrelation();

  return {
    gex, gamma_flip, flow_pressure, vol_regime, liquidity,
    unusual_activity, market_structure, stability, narrative, timeline,
    
    delta_exposure, vanna_charm, surface_3d, squeeze_metrics,
    live_tape, dark_pool, retail_inst, algo_clusters, trade_side,
    term_structure, vol_cones, skew_index, expected_move, earnings_crush,
    max_pain, volume_profile, synthetic_arb, sector_correlation
  };
}
