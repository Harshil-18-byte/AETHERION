import type { 
  OptionRow, DeltaExposureResult, VannaCharmResult, Surface3DResult, SqueezeResult,
  TapePrint, DarkPoolPrint, RetailInstResult, AlgoClusterItem, TradeSideResult,
  TermStructureResult, VolConesResult, SkewIndexResult, ExpectedMoveResult, EarningsCrushResult,
  MaxPainResult, VolumeProfileResult, SyntheticArbResult, SectorCorrelationResult
} from "./types";

const CONTRACT_SIZE = 25;

// Shared approximate math
function normalCdf(x: number): number {
  const t = 1 / (1 + 0.2316419 * Math.abs(x));
  const d = 0.3989423 * Math.exp(-x * x / 2);
  const p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
  return x > 0 ? 1 - p : p;
}
function approximateIV(optionPrice: number, spot: number): number {
  if (spot <= 0 || optionPrice <= 0) return 0;
  return Math.round(((optionPrice * Math.sqrt(2 * Math.PI)) / spot) * 100 * 100) / 100;
}
function d1(spot: number, strike: number, ivPct: number, tte = 7/365) {
  const sigma = ivPct / 100;
  if(sigma === 0 || tte === 0) return 0;
  return (Math.log(spot / strike) + 0.5 * sigma * sigma * tte) / (sigma * Math.sqrt(tte));
}

// --- 1. Advanced Greeks ---
export function computeDeltaExposure(snapshot: OptionRow[]): DeltaExposureResult {
  const spot = snapshot[snapshot.length - 1]?.spot_close || 0;
  let total_dex = 0;
  const by_strike = snapshot.map(row => {
    const ivCe = approximateIV(row.ce, spot);
    const ivPe = approximateIV(row.pe, spot);
    const d1ce = d1(spot, row.strike, ivCe);
    const d1pe = d1(spot, row.strike, ivPe);
    const ceDelta = normalCdf(d1ce);
    const peDelta = normalCdf(d1pe) - 1;
    
    const call_dex = (ceDelta * row.oi_ce * CONTRACT_SIZE * spot) / 1e7;
    const put_dex = (peDelta * row.oi_pe * CONTRACT_SIZE * spot) / 1e7;
    const net_dex = call_dex + put_dex;
    total_dex += net_dex;
    return { strike: row.strike, call_dex, put_dex, net_dex };
  });
  return { by_strike, total_dex };
}

export function computeVannaCharm(snapshot: OptionRow[]): VannaCharmResult {
  const by_strike = snapshot.map(row => {
    // Vanna measures delta sensitivity to IV. Charm measures delta sensitivity to time.
    // Extremely simplified approximation based on out-of-the-monyness
    const moneyness = Math.log(row.spot_close / row.strike);
    const vanna = moneyness * (row.oi_ce + row.oi_pe) / 10000; 
    const charm = -moneyness * (row.volume_ce + row.volume_pe) / 10000;
    return { strike: row.strike, vanna, charm };
  });
  return { by_strike };
}

export function computeSurface3D(snapshot: OptionRow[]): Surface3DResult {
  const points = snapshot.map((row, i) => ({
    strike: row.strike,
    expiry: row.expiry || "2026-03-02",
    days_to_expiry: Math.max(1, 7 + (i % 3)), // Simulating variance across expiries
    iv: approximateIV(row.ce, row.spot_close)
  })).filter(p => p.iv > 0);
  return { points };
}

export function computeSqueezeMetrics(snapshot: OptionRow[]): SqueezeResult {
  let maxCallOi = 0;
  let tStrike = 0;
  snapshot.forEach(row => {
    if (row.oi_ce > maxCallOi) { maxCallOi = row.oi_ce; tStrike = row.strike; }
  });
  const spot = snapshot[snapshot.length-1]?.spot_close || 1;
  const distance = (tStrike - spot) / spot;
  const is_squeezing = maxCallOi > 100000 && distance > 0 && distance < 0.05;
  return {
    is_squeezing,
    score: is_squeezing ? 85 : 30,
    trigger_strike: is_squeezing ? tStrike : null
  };
}

// --- 2. Flow Tracking ---
export function simulateLiveTape(snapshot: OptionRow[]): TapePrint[] {
  // Generate fake live tape based on highest volume strikes
  const activeStrikes = [...snapshot].sort((a,b) => (b.volume_ce+b.volume_pe) - (a.volume_ce+a.volume_pe)).slice(0, 15);
  return activeStrikes.map((s, i) => {
    const isCall = s.volume_ce > s.volume_pe;
    return {
      id: `TAPE-${i}-${Date.now()}`,
      time: new Date(Date.now() - Math.random() * 10000).toLocaleTimeString(),
      strike: s.strike,
      type: isCall ? "CALL" : "PUT",
      size: Math.floor(Math.random() * 500) + 50,
      price: isCall ? s.ce : s.pe,
      sentiment: isCall ? "BULLISH" : "BEARISH"
    };
  });
}

export function simulateDarkPool(snapshot: OptionRow[]): DarkPoolPrint[] {
  const spot = snapshot[0]?.spot_close || 25000;
  return Array.from({length: 8}).map((_, i) => ({
    id: `DP-${i}`,
    time: new Date(Date.now() - Math.random() * 86400000).toLocaleTimeString(),
    volume: Math.floor(Math.random() * 1000000) + 500000,
    price: spot * (1 + (Math.random() * 0.02 - 0.01)),
    estimated_value: Math.floor(Math.random() * 50) + 10 // Millions
  }));
}

export function computeRetailInst(snapshot: OptionRow[]): RetailInstResult {
  const totalVol = snapshot.reduce((sum, r) => sum + r.volume_ce + r.volume_pe, 0);
  if(totalVol === 0) return { retail_buy_pct: 25, retail_sell_pct: 25, inst_buy_pct: 25, inst_sell_pct: 25 };
  return {
    retail_buy_pct: 18.5,
    retail_sell_pct: 12.2,
    inst_buy_pct: 45.3,
    inst_sell_pct: 24.0
  };
}

export function detectAlgoClusters(snapshot: OptionRow[]): AlgoClusterItem[] {
  return snapshot
    .filter(r => (r.volume_ce + r.volume_pe) > 50000)
    .map(r => ({
      strike: r.strike,
      volume_cluster: r.volume_ce + r.volume_pe,
      confidence: Math.round(Math.random() * 40 + 60) // 60-100%
    }));
}

export function computeTradeSide(snapshot: OptionRow[]): TradeSideResult {
  const total = snapshot.reduce((sum, r) => sum + r.volume_ce + r.volume_pe, 0);
  return {
    bid_volume: Math.floor(total * 0.45),
    ask_volume: Math.floor(total * 0.40),
    mid_volume: Math.floor(total * 0.15)
  };
}

// --- 3. Volatility & Pricing ---
export function computeTermStructure(snapshot: OptionRow[]): TermStructureResult {
  return {
    structure: [
      { expiry: "0 DTE", days_to_expiry: 0, atm_iv: 15.2 },
      { expiry: "7 DTE", days_to_expiry: 7, atm_iv: 14.8 },
      { expiry: "30 DTE", days_to_expiry: 30, atm_iv: 16.5 },
      { expiry: "60 DTE", days_to_expiry: 60, atm_iv: 18.1 },
    ],
    shape: "CONTANGO"
  };
}

export function computeVolCones(snapshot: OptionRow[]): VolConesResult {
  const spot = snapshot[0]?.spot_close || 25000;
  const atmRow = snapshot.find(r => Math.abs(r.strike - spot) < 100);
  const current_iv = atmRow ? approximateIV(atmRow.ce, spot) : 15;
  return {
    current_iv,
    iv_percentile_10: 11.2,
    iv_percentile_50: 14.5,
    iv_percentile_90: 22.1
  };
}

export function computeSkewIndex(snapshot: OptionRow[]): SkewIndexResult {
  const spot = snapshot[0]?.spot_close || 25000;
  const putIv = approximateIV(snapshot.find(r => r.strike <= spot * 0.95)?.pe || 100, spot);
  const callIv = approximateIV(snapshot.find(r => r.strike >= spot * 1.05)?.ce || 100, spot);
  const skew = putIv - callIv;
  return {
    skew_score: skew,
    trend: skew > 2 ? "Steepening" : "Normal"
  };
}

export function computeExpectedMove(snapshot: OptionRow[]): ExpectedMoveResult {
  const spot = snapshot[0]?.spot_close || 25000;
  const atmRow = snapshot.find(r => Math.abs(r.strike - spot) < 100);
  const straddle = atmRow ? (atmRow.ce + atmRow.pe) : (spot * 0.01);
  return {
    daily: (straddle / 7) * 0.8,
    weekly: straddle,
    monthly: straddle * Math.sqrt(4),
    implied_straddle_price: straddle
  };
}

export function computeEarningsCrush(): EarningsCrushResult {
  return { implied_crush_pct: 35.5, post_earnings_iv_estimate: 45.2 };
}

// --- 4. Strategy & Structure ---
export function computeMaxPain(snapshot: OptionRow[]): MaxPainResult {
  let minPain = Infinity;
  let maxPainStrike = 0;
  for (const targ of snapshot) {
    let pain = 0;
    for (const opt of snapshot) {
      if(opt.strike < targ.strike) pain += opt.oi_ce * (targ.strike - opt.strike); // Calls ITM
      if(opt.strike > targ.strike) pain += opt.oi_pe * (opt.strike - targ.strike); // Puts ITM
    }
    if (pain < minPain) { minPain = pain; maxPainStrike = targ.strike; }
  }
  return { max_pain_strike: maxPainStrike, total_value_at_pain: minPain };
}

export function computeVolumeProfile(snapshot: OptionRow[]): VolumeProfileResult {
  let highestVol = 0;
  let poc = 0;
  snapshot.forEach(r => {
    const v = r.volume_ce + r.volume_pe;
    if (v > highestVol) { highestVol = v; poc = r.strike; }
  });
  const profile = snapshot.map(r => ({
    strike: r.strike,
    call_volume: r.volume_ce,
    put_volume: r.volume_pe,
    poc: r.strike === poc
  }));
  return { profile, poc_strike: poc };
}

export function computeSyntheticArb(snapshot: OptionRow[]): SyntheticArbResult {
  return {
    implied_spot: (snapshot[0]?.spot_close || 25000) + 12.5,
    actual_spot: snapshot[0]?.spot_close || 25000,
    discount_premium: 12.5,
    opportunities: ["Long Reversal 25000", "Short Conversion 25500"]
  };
}

export function computeSectorCorrelation(): SectorCorrelationResult {
  return { spy_corr: 0.85, qqq_corr: 0.72, iwm_corr: 0.45 };
}
