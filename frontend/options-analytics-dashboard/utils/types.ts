// TypeScript interfaces for options analytics data

export interface OptionRow {
  symbol: string;
  datetime: string;
  expiry: string;
  ce: number;
  pe: number;
  spot_close: number;
  atm: number;
  strike: number;
  oi_ce: number;
  oi_pe: number;
  volume_ce: number;
  volume_pe: number;
}

export interface GEXByStrike {
  strike: number;
  call_gex: number;
  put_gex: number;
  net_gex: number;
  iv_ce: number;
  iv_pe: number;
}

export interface GEXResult {
  by_strike: GEXByStrike[];
  total_gex: number;
  spot: number;
  interpretation: string;
}

export interface CumulativeGEX {
  strike: number;
  cumulative_gex: number;
}

export interface GammaFlipResult {
  gamma_flip_level: number | null;
  cumulative_gex: CumulativeGEX[];
}

export interface FlowByStrike {
  strike: number;
  call_volume: number;
  put_volume: number;
  strike_pressure: number;
}

export interface FlowPressureResult {
  flow_pressure: number;
  sentiment: string;
  total_call_volume: number;
  total_put_volume: number;
  by_strike: FlowByStrike[];
}

export interface IVByStrike {
  strike: number;
  iv: number;
}

export interface VolRegimeResult {
  regime: string;
  mean_iv: number;
  std_iv: number;
  cv: number;
  atm_iv: number;
  iv_by_strike: IVByStrike[];
}

export interface LiquidityItem {
  strike: number;
  total_oi: number;
  total_volume: number;
  call_oi: number;
  put_oi: number;
  liquidity_score: number;
}

export interface LiquidityResult {
  clusters: LiquidityItem[];
  liquidity_map: LiquidityItem[];
  threshold: number;
}

export interface UnusualAlert {
  strike: number;
  total_volume: number;
  call_volume: number;
  put_volume: number;
  z_score: number;
  pct_above_mean: number;
  type: string;
}

export interface UnusualActivityResult {
  alerts: UnusualAlert[];
  has_unusual_activity: boolean;
  mean_volume: number;
  std_volume: number;
}

export interface MarketStructureResult {
  support: number;
  support_oi: number;
  resistance: number;
  resistance_oi: number;
  spot: number;
  pcr: number;
  range: string;
}

export interface StabilityResult {
  score: number;
  status: string;
  components: Record<string, number>;
}

export interface TimelineEvent {
  time: string;
  event: string;
  severity: "high" | "medium" | "low";
}

// --- Advanced Greeks ---
export interface DeltaExposureItem { strike: number; call_dex: number; put_dex: number; net_dex: number; }
export interface DeltaExposureResult { by_strike: DeltaExposureItem[]; total_dex: number; }
export interface VannaCharmItem { strike: number; vanna: number; charm: number; }
export interface VannaCharmResult { by_strike: VannaCharmItem[]; }
export interface Surface3DPoint { strike: number; expiry: string; days_to_expiry: number; iv: number; }
export interface Surface3DResult { points: Surface3DPoint[]; }
export interface SqueezeResult { is_squeezing: boolean; score: number; trigger_strike: number | null; }

// --- Flow Tracking ---
export interface TapePrint { id: string; time: string; strike: number; type: "CALL" | "PUT"; size: number; price: number; sentiment: "BULLISH" | "BEARISH" | "NEUTRAL"; }
export interface DarkPoolPrint { id: string; time: string; volume: number; price: number; estimated_value: number; }
export interface RetailInstResult { retail_buy_pct: number; retail_sell_pct: number; inst_buy_pct: number; inst_sell_pct: number; }
export interface AlgoClusterItem { strike: number; volume_cluster: number; confidence: number; }
export interface TradeSideResult { bid_volume: number; ask_volume: number; mid_volume: number; }

// --- Volatility & Pricing ---
export interface TermStructureItem { expiry: string; days_to_expiry: number; atm_iv: number; }
export interface TermStructureResult { structure: TermStructureItem[]; shape: "CONTANGO" | "BACKWARDATION" | "FLAT"; }
export interface VolConesResult { current_iv: number; iv_percentile_10: number; iv_percentile_50: number; iv_percentile_90: number; }
export interface SkewIndexResult { skew_score: number; trend: string; }
export interface ExpectedMoveResult { daily: number; weekly: number; monthly: number; implied_straddle_price: number; }
export interface EarningsCrushResult { implied_crush_pct: number; post_earnings_iv_estimate: number; }

// --- Strategy & Structure ---
export interface MaxPainResult { max_pain_strike: number; total_value_at_pain: number; }
export interface VolumeProfileItem { strike: number; call_volume: number; put_volume: number; poc: boolean; }
export interface VolumeProfileResult { profile: VolumeProfileItem[]; poc_strike: number; }
export interface SyntheticArbResult { implied_spot: number; actual_spot: number; discount_premium: number; opportunities: string[]; }
export interface SectorCorrelationResult { spy_corr: number; qqq_corr: number; iwm_corr: number; }

export interface FullAnalysis {
  gex: GEXResult;
  gamma_flip: GammaFlipResult;
  flow_pressure: FlowPressureResult;
  vol_regime: VolRegimeResult;
  liquidity: LiquidityResult;
  unusual_activity: UnusualActivityResult;
  market_structure: MarketStructureResult;
  stability: StabilityResult;
  narrative: string;
  timeline: TimelineEvent[];
  
  // New 20 Feature Extensions
  delta_exposure?: DeltaExposureResult;
  vanna_charm?: VannaCharmResult;
  surface_3d?: Surface3DResult;
  squeeze_metrics?: SqueezeResult;
  
  live_tape?: TapePrint[];
  dark_pool?: DarkPoolPrint[];
  retail_inst?: RetailInstResult;
  algo_clusters?: AlgoClusterItem[];
  trade_side?: TradeSideResult;
  
  term_structure?: TermStructureResult;
  vol_cones?: VolConesResult;
  skew_index?: SkewIndexResult;
  expected_move?: ExpectedMoveResult;
  earnings_crush?: EarningsCrushResult;
  
  max_pain?: MaxPainResult;
  volume_profile?: VolumeProfileResult;
  synthetic_arb?: SyntheticArbResult;
  sector_correlation?: SectorCorrelationResult;
}
