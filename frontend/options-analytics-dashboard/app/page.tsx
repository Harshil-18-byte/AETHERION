"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import dynamic from "next/dynamic";
import TopNav from "@/components/TopNav";
import EventTimeline from "@/components/EventTimeline";
import AuthGuard from "@/components/AuthGuard";
import { fetchAnalysis, uploadAnalysis } from "@/services/api";
import type { FullAnalysis } from "@/utils/types";

// Dynamic imports for chart components
const OIChart = dynamic(() => import("@/charts/OIChart"), { ssr: false });
const VolumeChart = dynamic(() => import("@/charts/VolumeChart"), { ssr: false });
const GEXChart = dynamic(() => import("@/charts/GEXChart"), { ssr: false });
const LiquidityHeatmap = dynamic(() => import("@/charts/LiquidityHeatmap"), { ssr: false });
const VolSmileChart = dynamic(() => import("@/charts/VolSmileChart"), { ssr: false });
const FlowChart = dynamic(() => import("@/charts/FlowChart"), { ssr: false });

const DEXChart = dynamic(() => import("@/charts/DEXChart"), { ssr: false });
const VannaCharmChart = dynamic(() => import("@/charts/VannaCharmChart"), { ssr: false });
const ExpectedMoveChart = dynamic(() => import("@/charts/ExpectedMoveChart"), { ssr: false });
const VolConesChart = dynamic(() => import("@/charts/VolConesChart"), { ssr: false });
const MaxPainChart = dynamic(() => import("@/charts/MaxPainChart"), { ssr: false });
const VolumeProfileChart = dynamic(() => import("@/charts/VolumeProfileChart"), { ssr: false });

const StrategyBuilder = dynamic(() => import("@/components/StrategyBuilder"), { ssr: false });
const LiveTape = dynamic(() => import("@/components/LiveTape"), { ssr: false });
const DarkPoolFeed = dynamic(() => import("@/components/DarkPoolFeed"), { ssr: false });

export default function Dashboard() {
  const [analysis, setAnalysis] = useState<FullAnalysis | null>(null);
  const [expiries, setExpiries] = useState<string[]>([]);
  const [selectedExpiry, setSelectedExpiry] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  // Terminal State
  const [activeCommand, setActiveCommand] = useState("OVERVIEW");
  const [commandInput, setCommandInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus & Filter State
  const [focusedStrike, setFocusedStrike] = useState<number | null>(null);
  const [strikeRange, setStrikeRange] = useState<string>("all");
  const [timeWindow, setTimeWindow] = useState<string>("latest");

  const loadAnalysis = useCallback(async (expiry?: string) => {
    try {
      setLoading(true);
      setError(null);
      console.log(`[Dashboard] Loading analysis for expiry: ${expiry || 'latest'}`);
      const result = await fetchAnalysis(expiry);
      console.log(`[Dashboard] API Result:`, result);
      setExpiries(result.expiries);
      setSelectedExpiry(result.selected_expiry);
      setAnalysis(result.analysis);
      setLastUpdated(new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }));
      setFocusedStrike(result.analysis.market_structure.spot); // Init focus on spot
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAnalysis();
  }, [loadAnalysis]);

  // Terminal command handling
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Focus command input on pressing '/'
      if (e.key === "/" && document.activeElement !== inputRef.current) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleCommandSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cmd = commandInput.toUpperCase().trim();
    const validCommands = ["OVERVIEW", "STRUCTURE", "GREEKS", "VOLATILITY", "LIQUIDITY", "FLOW", "STRATEGY", "OI", "VOL", "GEX"];
    
    if (validCommands.includes(cmd)) {
      if (cmd === "OI" || cmd === "VOL") setActiveCommand("STRUCTURE");
      else if (cmd === "GEX") setActiveCommand("GREEKS");
      else setActiveCommand(cmd);
      setCommandInput("");
      inputRef.current?.blur();
    }
  };

  const handleExpiryChange = (expiry: string) => {
    setSelectedExpiry(expiry);
    loadAnalysis(expiry);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setLoading(true);
      setError(null);
      const result = await uploadAnalysis(file);
      setExpiries(result.expiries);
      setSelectedExpiry(result.selected_expiry);
      setAnalysis(result.analysis);
      setLastUpdated(new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) + " (Custom)");
      setFocusedStrike(result.analysis.market_structure.spot);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load custom dataset");
    } finally {
      setLoading(false);
      // Reset input value so same file can be selected again
      e.target.value = "";
    }
  };

  // Consolidated Chart Interactions
  const chartEvents = useMemo(() => ({
    onHover: (s: number) => setFocusedStrike(s),
    onClick: (s: number) => setFocusedStrike(s),
    mouseover: (params: { name?: string | number }) => {
      if (params.name) {
        const s = parseInt(params.name.toString(), 10);
        if (!isNaN(s)) setFocusedStrike(s);
      }
    }
  }), []);

  // Memoized Chart Data & Events (Must be before conditional returns)
  const oiData = useMemo(() => {
    if (!analysis?.liquidity?.liquidity_map) return [];
    return analysis.liquidity.liquidity_map.map(d => ({
      strike: d.strike, call_oi: d.call_oi, put_oi: d.put_oi,
    }));
  }, [analysis]);

  const volumeData = useMemo(() => {
    if (!analysis?.flow_pressure?.by_strike) return [];
    return analysis.flow_pressure.by_strike.map(d => ({
      strike: d.strike, call_volume: d.call_volume, put_volume: d.put_volume,
    }));
  }, [analysis]);

  const focusData = useMemo(() => {
    if (!analysis?.liquidity?.liquidity_map) return null;
    return analysis.liquidity.liquidity_map.find(d => d.strike === focusedStrike) || analysis.liquidity.liquidity_map[0];
  }, [analysis, focusedStrike]);

  const gexFocus = useMemo(() => {
    if (!analysis?.gex?.by_strike) return null;
    return analysis.gex.by_strike.find(d => d.strike === focusedStrike);
  }, [analysis, focusedStrike]);

  // ── States ────────────────────────────────────────────────────────
  if (loading && !analysis) {
    return (
      <AuthGuard>
        <div className="loading-container">
          <span className="loading-brand">GammaLens Terminal</span>
          <div className="loading-bar"><div className="loading-bar-inner" /></div>
          <span className="loading-text">Initializing analytics workspace...</span>
        </div>
      </AuthGuard>
    );
  }

  if (error && !analysis) {
    return (
      <AuthGuard>
        <div className="error-container">
          <span className="error-title">Terminal Connection Restored</span>
          <span className="error-message">{error}</span>
          <button className="error-retry-btn" onClick={() => loadAnalysis()}>Reconnect</button>
        </div>
      </AuthGuard>
    );
  }

  if (!analysis) return null;

  const { gex, gamma_flip, flow_pressure, vol_regime, liquidity,
          market_structure, stability, narrative, timeline } = analysis;

  const sentimentType = flow_pressure.sentiment.toLowerCase().includes("bullish") ? "positive"
    : flow_pressure.sentiment.toLowerCase().includes("bearish") ? "negative"
    : "neutral";

  return (
    <AuthGuard>
      <div className="terminal-layout">
        <TopNav
          selectedExpiry={selectedExpiry}
          expiries={expiries}
          onExpiryChange={handleExpiryChange}
          lastUpdated={lastUpdated}
          spotPrice={market_structure.spot}
          onFileUpload={handleFileUpload}
        />

        {/* ── Command Bar ─────────────────────────────────────────── */}
        <div className="command-bar terminal-panel">
          <form className="command-input-wrapper" onSubmit={handleCommandSubmit}>
            <span className="command-prompt text-amber mono">{'>'}</span>
            <input
              ref={inputRef}
              type="text"
              className="command-input mono"
              value={commandInput}
              onChange={(e) => setCommandInput(e.target.value)}
              placeholder="STRUC <GO>, VOLATILITY <GO>..."
            />
          </form>

          <div className="command-tabs">
            {["OVERVIEW", "STRUCTURE", "GREEKS", "VOLATILITY", "LIQUIDITY", "FLOW", "STRATEGY"].map(cmd => (
              <button
                key={cmd}
                className={`command-tab ${activeCommand === cmd ? "active" : ""}`}
                onClick={() => setActiveCommand(cmd)}
              >
                {cmd}
              </button>
            ))}
          </div>

          <div className="command-filters">
            <div className="filter-group">
              <span className="filter-label">Range</span>
              <select className="filter-select" value={strikeRange} onChange={(e) => setStrikeRange(e.target.value)}>
                <option value="all">ALL</option>
                <option value="atm10">±10 ATM</option>
                <option value="atm20">±20 ATM</option>
              </select>
            </div>
            <div className="filter-group">
              <span className="filter-label">Time</span>
              <select className="filter-select" value={timeWindow} onChange={(e) => setTimeWindow(e.target.value)}>
                <option value="latest">LATEST</option>
                <option value="15m">15 MIN</option>
                <option value="30m">30 MIN</option>
              </select>
            </div>
          </div>
        </div>

        <div className="terminal-body">
          {/* ── Market Intelligence Sidebar ────────────────────────── */}
          <aside className="intel-sidebar animate-in stagger-1">
            <div className="sidebar-header">MARKET INTELLIGENCE</div>
            
            <div className="intel-panel terminal-panel">
              <div className="intel-row">
                <span className="intel-label mono">SENTIMENT</span>
                <span className={`intel-value mono intel-${sentimentType}`}>{flow_pressure.sentiment.toUpperCase()}</span>
              </div>
              <div className="intel-row">
                <span className="intel-label mono">FLOW_PR</span>
                <span className={`intel-value mono intel-${sentimentType}`}>{flow_pressure.flow_pressure.toFixed(3)}</span>
              </div>
              <div className="intel-row">
                <span className="intel-label mono">SUPP_LVL</span>
                <span className="intel-value mono text-cyan">{market_structure.support.toLocaleString()}</span>
              </div>
              <div className="intel-row">
                <span className="intel-label mono">RES_LVL</span>
                <span className="intel-value mono text-red">{market_structure.resistance.toLocaleString()}</span>
              </div>
              <div className="intel-row">
                <span className="intel-label mono">VOL_REGIME</span>
                <span className="intel-value mono text-amber">{vol_regime.regime.toUpperCase()}</span>
              </div>
              <div className="intel-row">
                <span className="intel-label mono">GAMMA_BIAS</span>
                <span className="intel-value mono">{gex.total_gex > 0 ? "LONG" : "SHORT"}</span>
              </div>
              <div className="metric-grid-overlay" />
            </div>

            <div className="sidebar-header mt-4 mono">STABILITY SCORE</div>
            <div className="intel-panel terminal-panel">
               <div className="stability-main">
                 <span className="stability-huge mono">{stability.score.toFixed(0)}</span>
                 <span className="stability-sub mono">/ 100</span>
               </div>
               {Object.entries(stability.components).map(([key, value]) => (
                  <div key={key} className="intel-row">
                    <span className="intel-label mono">{key.replace(/_/g, " ").toUpperCase()}</span>
                    <span className="intel-value mono">{value.toFixed(0)}</span>
                  </div>
               ))}
               <div className="metric-grid-overlay" />
            </div>

            <div className="sidebar-header mt-4 mono">MARKET NARRATIVE</div>
            <div className="intel-panel terminal-panel">
              <p className="narrative-mini mono text-secondary">{narrative}</p>
              <div className="metric-grid-overlay" />
            </div>
          </aside>

          {/* ── Main Workspace ─────────────────────────────────────── */}
          <main className="terminal-workspace animate-in stagger-2">
            {activeCommand === "OVERVIEW" && (
              <div className="workspace-grid workspace-overview">
                <div className="panel panel-span-2">
                  <div className="panel-header">EXPECTED MOVE BOUNDARIES</div>
                  <div className="panel-body">
                    {analysis.expected_move ? (
                      <ExpectedMoveChart data={analysis.expected_move} spot={gex.spot} />
                    ) : (
                      <div className="chart-placeholder">Expected move data unavailable</div>
                    )}
                  </div>
                </div>
                <div className="panel">
                  <div className="panel-header">OPEN INTEREST PROFILE</div>
                  <div className="panel-body"><OIChart data={oiData} onEvents={chartEvents} /></div>
                </div>
                <div className="panel panel-span-2">
                  <div className="panel-header">LIQUIDITY HEATMAP</div>
                  <div className="panel-body"><LiquidityHeatmap data={liquidity.liquidity_map || []} onEvents={chartEvents} /></div>
                </div>
              </div>
            )}

            {activeCommand === "STRUCTURE" && (
              <div className="workspace-grid workspace-2col">
                <div className="panel">
                  <div className="panel-header">MAX PAIN DISTRIBUTION</div>
                  <div className="panel-body">
                    {analysis.max_pain ? (
                      <MaxPainChart data={analysis.max_pain} snapshot={liquidity.liquidity_map || []} />
                    ) : (
                      <div className="chart-placeholder">Max pain data unavailable</div>
                    )}
                  </div>
                </div>
                <div className="panel">
                  <div className="panel-header">OPTIONS VOLUME PROFILE</div>
                  <div className="panel-body">
                    {analysis.volume_profile ? (
                      <VolumeProfileChart data={analysis.volume_profile} />
                    ) : (
                      <div className="chart-placeholder">Volume profile unavailable</div>
                    )}
                  </div>
                </div>
                <div className="panel">
                  <div className="panel-header">OPEN INTEREST ANALYSIS</div>
                  <div className="panel-body"><OIChart data={oiData} onEvents={chartEvents} /></div>
                </div>
                <div className="panel">
                  <div className="panel-header">VOLUME ANALYSIS</div>
                  <div className="panel-body"><VolumeChart data={volumeData} onEvents={chartEvents} /></div>
                </div>
              </div>
            )}

            {activeCommand === "GREEKS" && (
              <div className="workspace-grid workspace-2col">
                <div className="panel">
                  <div className="panel-header">DEALER DELTA EXPOSURE (DEX)</div>
                  <div className="panel-body">
                    {analysis.delta_exposure?.by_strike ? (
                      <DEXChart data={analysis.delta_exposure.by_strike} />
                    ) : (
                      <div className="chart-placeholder">DEX data unavailable</div>
                    )}
                  </div>
                </div>
                <div className="panel">
                  <div className="panel-header">VANNA & CHARM EXPOSURE</div>
                  <div className="panel-body">
                    {analysis.vanna_charm?.by_strike ? (
                      <VannaCharmChart data={analysis.vanna_charm.by_strike} />
                    ) : (
                      <div className="chart-placeholder">Vanna/Charm data unavailable</div>
                    )}
                  </div>
                </div>
                <div className="panel panel-span-2">
                  <div className="panel-header">GAMMA EXPOSURE (GEX)</div>
                  <div className="panel-body"><GEXChart data={gex.by_strike || []} gammaFlipLevel={gamma_flip?.gamma_flip_level} spot={gex.spot} /></div>
                </div>
              </div>
            )}

            {activeCommand === "VOLATILITY" && (
              <div className="workspace-grid workspace-2col">
                <div className="panel">
                  <div className="panel-header">HISTORICAL VOLATILITY CONES</div>
                  <div className="panel-body">
                    {analysis.vol_cones ? (
                      <VolConesChart data={analysis.vol_cones} />
                    ) : (
                      <div className="chart-placeholder">Vol cones unavailable</div>
                    )}
                  </div>
                </div>
                <div className="panel">
                  <div className="panel-header">VOLATILITY SMILE</div>
                  <div className="panel-body"><VolSmileChart data={vol_regime.iv_by_strike || []} spot={gex.spot} onEvents={chartEvents} /></div>
                </div>
              </div>
            )}

            {activeCommand === "LIQUIDITY" && (
              <div className="workspace-grid workspace-1col">
                <div className="panel">
                  <div className="panel-header">CROSS-SECTIONAL LIQUIDITY MAP</div>
                  <div className="panel-body"><LiquidityHeatmap data={liquidity.liquidity_map} onEvents={chartEvents} /></div>
                </div>
              </div>
            )}

            {activeCommand === "FLOW" && (
              <div className="workspace-grid workspace-2col">
                <div className="panel panel-span-2 terminal-panel">
                  <div className="panel-header mono">NET FLOW PRESSURE BY STRIKE</div>
                  <div className="panel-body" style={{ height: "300px" }}><FlowChart data={flow_pressure.by_strike} onEvents={chartEvents} /></div>
                  <div className="metric-grid-overlay" />
                </div>
                <div className="panel terminal-panel" style={{ height: "400px" }}>
                  <div className="panel-header mono">LIVE OPTIONS TAPE</div>
                  <LiveTape />
                  <div className="metric-grid-overlay" />
                </div>
                <div className="panel terminal-panel" style={{ height: "400px" }}>
                  <div className="panel-header mono">DARK POOL FEED</div>
                  <DarkPoolFeed />
                  <div className="metric-grid-overlay" />
                </div>
              </div>
            )}

            {activeCommand === "STRATEGY" && (
              <div className="workspace-grid workspace-1col" style={{ minHeight: "650px" }}>
                <div className="panel terminal-panel">
                  <div className="panel-header mono">STRATEGY BUILDER / PAYOFF OPTIMIZER</div>
                  <StrategyBuilder />
                  <div className="metric-grid-overlay" />
                </div>
              </div>
            )}
          </main>

          {/* ── Right Sidebar: Strike Focus & Events ───────────────── */}
          <aside className="focus-sidebar animate-in stagger-3">
            <div className="sidebar-header mono">STRIKE FOCUS: {focusedStrike || "-"}</div>
            {focusedStrike ? (
              <div className="focus-panel terminal-panel">
                <div className="focus-grid">
                  <div className="focus-box">
                    <span className="focus-lbl mono">CALL_OI</span>
                    <span className="focus-val mono text-cyan">{focusData?.call_oi.toLocaleString()}</span>
                  </div>
                  <div className="focus-box">
                    <span className="focus-lbl mono">PUT_OI</span>
                    <span className="focus-val mono text-red">{focusData?.put_oi.toLocaleString()}</span>
                  </div>
                  <div className="focus-box">
                    <span className="focus-lbl mono">NET_GEX</span>
                    <span className="focus-val mono">{gexFocus?.net_gex ? gexFocus.net_gex.toLocaleString() : "0"}</span>
                  </div>
                  <div className="focus-box">
                    <span className="focus-lbl mono">LIQ_SCR</span>
                    <span className="focus-val mono text-amber">{focusData?.liquidity_score.toFixed(2)}</span>
                  </div>
                </div>
                <div className="metric-grid-overlay" />
              </div>
            ) : (
              <div className="focus-empty">Hover a strike to view detailed analytics</div>
            )}

            <div className="sidebar-header mt-4">EVENT FEED</div>
            <div className="event-feed-panel">
              <EventTimeline events={timeline} />
            </div>
          </aside>
        </div>
      </div>
    </AuthGuard>
  );
}
