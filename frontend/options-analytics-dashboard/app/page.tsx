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
      const result = await fetchAnalysis(expiry);
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

  const syncStrike = (strikeStr: string) => {
    const s = parseInt(strikeStr, 10);
    if (!isNaN(s)) setFocusedStrike(s);
  };

  // Memoized Chart Data & Events (Must be before conditional returns)
  const oiData = useMemo(() => {
    if (!analysis) return [];
    return analysis.liquidity.liquidity_map.map(d => ({
      strike: d.strike, call_oi: d.call_oi, put_oi: d.put_oi,
    }));
  }, [analysis]);

  const volumeData = useMemo(() => {
    if (!analysis) return [];
    return analysis.flow_pressure.by_strike.map(d => ({
      strike: d.strike, call_volume: d.call_volume, put_volume: d.put_volume,
    }));
  }, [analysis]);

  const focusData = useMemo(() => {
    if (!analysis) return null;
    return analysis.liquidity.liquidity_map.find(d => d.strike === focusedStrike) || analysis.liquidity.liquidity_map[0];
  }, [analysis, focusedStrike]);

  const gexFocus = useMemo(() => {
    if (!analysis) return null;
    return analysis.gex.by_strike.find(d => d.strike === focusedStrike);
  }, [analysis, focusedStrike]);

  const chartEvents = useMemo(() => ({
    mouseover: (params: { name?: string | number }) => {
      if (params.name) {
        const s = parseInt(params.name.toString(), 10);
        if (!isNaN(s)) setFocusedStrike(s);
      }
    }
  }), []);

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
        <div className="command-bar">
          <form className="command-input-wrapper" onSubmit={handleCommandSubmit}>
            <span className="command-prompt">{'>'}</span>
            <input
              ref={inputRef}
              type="text"
              className="command-input"
              value={commandInput}
              onChange={(e) => setCommandInput(e.target.value)}
              placeholder="Type command (e.g. VOLATILITY) or press '/' to focus"
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
          <aside className="intel-sidebar">
            <div className="sidebar-header">MARKET INTELLIGENCE</div>
            
            <div className="intel-panel">
              <div className="intel-row">
                <span className="intel-label">Sentiment</span>
                <span className={`intel-value intel-${sentimentType}`}>{flow_pressure.sentiment}</span>
              </div>
              <div className="intel-row">
                <span className="intel-label">Flow Pressure</span>
                <span className={`intel-value intel-${sentimentType}`}>{flow_pressure.flow_pressure.toFixed(3)}</span>
              </div>
              <div className="intel-row">
                <span className="intel-label">Support Lvl</span>
                <span className="intel-value">{market_structure.support.toLocaleString()}</span>
              </div>
              <div className="intel-row">
                <span className="intel-label">Resist Lvl</span>
                <span className="intel-value">{market_structure.resistance.toLocaleString()}</span>
              </div>
              <div className="intel-row">
                <span className="intel-label">Vol Regime</span>
                <span className="intel-value intel-warn">{vol_regime.regime}</span>
              </div>
              <div className="intel-row">
                <span className="intel-label">Gamma Bias</span>
                <span className="intel-value">{gex.total_gex > 0 ? "Positive" : "Negative"}</span>
              </div>
            </div>

            <div className="sidebar-header mt-4">STABILITY SCORE</div>
            <div className="intel-panel">
               <div className="stability-main">
                 <span className="stability-huge">{stability.score.toFixed(0)}</span>
                 <span className="stability-sub">/ 100</span>
               </div>
               {Object.entries(stability.components).map(([key, value]) => (
                  <div key={key} className="intel-row">
                    <span className="intel-label">{key.replace(/_/g, " ")}</span>
                    <span className="intel-value">{value.toFixed(0)}</span>
                  </div>
               ))}
            </div>

            <div className="sidebar-header mt-4">MARKET NARRATIVE</div>
            <div className="intel-panel">
              <p className="narrative-mini">{narrative}</p>
            </div>
          </aside>

          {/* ── Main Workspace ─────────────────────────────────────── */}
          <main className="terminal-workspace">
            {activeCommand === "OVERVIEW" && (
              <div className="workspace-grid workspace-overview">
                <div className="panel panel-span-2">
                  <div className="panel-header">EXPECTED MOVE BOUNDARIES</div>
                  <div className="panel-body"><ExpectedMoveChart data={analysis.expected_move!} spot={gex.spot} /></div>
                </div>
                <div className="panel">
                  <div className="panel-header">OPEN INTEREST PROFILE</div>
                  <div className="panel-body"><OIChart data={oiData} onEvents={chartEvents} /></div>
                </div>
                <div className="panel panel-span-2">
                  <div className="panel-header">LIQUIDITY HEATMAP</div>
                  <div className="panel-body"><LiquidityHeatmap data={liquidity.liquidity_map} onEvents={chartEvents} /></div>
                </div>
              </div>
            )}

            {activeCommand === "STRUCTURE" && (
              <div className="workspace-grid workspace-2col">
                <div className="panel">
                  <div className="panel-header">MAX PAIN DISTRIBUTION</div>
                  <div className="panel-body"><MaxPainChart data={analysis.max_pain!} snapshot={liquidity.liquidity_map as any} /></div>
                </div>
                <div className="panel">
                  <div className="panel-header">OPTIONS VOLUME PROFILE</div>
                  <div className="panel-body"><VolumeProfileChart data={analysis.volume_profile!} /></div>
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
                  <div className="panel-body"><DEXChart data={analysis.delta_exposure!.by_strike} /></div>
                </div>
                <div className="panel">
                  <div className="panel-header">VANNA & CHARM EXPOSURE</div>
                  <div className="panel-body"><VannaCharmChart data={analysis.vanna_charm!.by_strike} /></div>
                </div>
                <div className="panel panel-span-2">
                  <div className="panel-header">GAMMA EXPOSURE (GEX)</div>
                  <div className="panel-body"><GEXChart data={gex.by_strike} gammaFlipLevel={gamma_flip.gamma_flip_level} spot={gex.spot} /></div>
                </div>
              </div>
            )}

            {activeCommand === "VOLATILITY" && (
              <div className="workspace-grid workspace-2col">
                <div className="panel">
                  <div className="panel-header">HISTORICAL VOLATILITY CONES</div>
                  <div className="panel-body"><VolConesChart data={analysis.vol_cones!} /></div>
                </div>
                <div className="panel">
                  <div className="panel-header">VOLATILITY SMILE</div>
                  <div className="panel-body"><VolSmileChart data={vol_regime.iv_by_strike} spot={gex.spot} onEvents={chartEvents} /></div>
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
                <div className="panel panel-span-2">
                  <div className="panel-header">NET FLOW PRESSURE BY STRIKE</div>
                  <div className="panel-body" style={{ height: "300px" }}><FlowChart data={flow_pressure.by_strike} onEvents={chartEvents} /></div>
                </div>
                <div className="panel" style={{ height: "400px" }}>
                  <LiveTape />
                </div>
                <div className="panel" style={{ height: "400px" }}>
                  <DarkPoolFeed />
                </div>
              </div>
            )}

            {activeCommand === "STRATEGY" && (
              <div className="workspace-grid workspace-1col" style={{ minHeight: "650px" }}>
                <StrategyBuilder />
              </div>
            )}
          </main>

          {/* ── Right Sidebar: Strike Focus & Events ───────────────── */}
          <aside className="focus-sidebar">
            <div className="sidebar-header">STRIKE FOCUS: {focusedStrike || "-"}</div>
            {focusedStrike ? (
              <div className="focus-panel">
                <div className="focus-grid">
                  <div className="focus-box">
                    <span className="focus-lbl">Call OI</span>
                    <span className="focus-val text-accent">{focusData?.call_oi.toLocaleString()}</span>
                  </div>
                  <div className="focus-box">
                    <span className="focus-lbl">Put OI</span>
                    <span className="focus-val text-red">{focusData?.put_oi.toLocaleString()}</span>
                  </div>
                  <div className="focus-box">
                    <span className="focus-lbl">Net GEX</span>
                    <span className="focus-val">{gexFocus?.net_gex ? gexFocus.net_gex.toLocaleString() : "0"}</span>
                  </div>
                  <div className="focus-box">
                    <span className="focus-lbl">Liquidity</span>
                    <span className="focus-val">{focusData?.liquidity_score.toFixed(2)}</span>
                  </div>
                </div>
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
