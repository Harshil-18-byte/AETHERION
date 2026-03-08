"use client";

import type { MarketStructureResult, VolRegimeResult, UnusualActivityResult } from "@/utils/types";

interface IntelligencePanelProps {
  structure: MarketStructureResult;
  volRegime: VolRegimeResult;
  unusual: UnusualActivityResult;
  flowSentiment?: string;
  flowPressure?: number;
  loading?: boolean;
  error?: string;
}

export default function IntelligencePanel({ structure, volRegime, unusual, flowSentiment, flowPressure, loading, error }: IntelligencePanelProps) {
  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <span className="card-title">Market Intelligence</span>
        </div>
        <div className="component-loading">
          <div className="component-loading-bar">
            <div className="component-loading-bar-inner" />
          </div>
          <span className="component-loading-text">Loading market intelligence...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-header">
          <span className="card-title">Market Intelligence</span>
        </div>
        <div className="component-error">Unable to load analytics data.</div>
      </div>
    );
  }

  // Determine sentiment display
  const sentimentDisplay = flowSentiment || "N/A";
  const sentimentClass = sentimentDisplay.toLowerCase().includes("bullish")
    ? "intel-summary-value intel-summary-value-positive"
    : sentimentDisplay.toLowerCase().includes("bearish")
      ? "intel-summary-value intel-summary-value-negative"
      : "intel-summary-value";

  const regimeClass = volRegime.regime === "Expansion"
    ? "intel-summary-value intel-summary-value-warn"
    : volRegime.regime === "Compression"
      ? "intel-summary-value intel-summary-value-positive"
      : "intel-summary-value";

  const pressureClass = flowPressure != null && flowPressure > 0
    ? "intel-summary-value intel-summary-value-positive"
    : flowPressure != null && flowPressure < 0
      ? "intel-summary-value intel-summary-value-negative"
      : "intel-summary-value";

  return (
    <>
      {/* Key Intelligence Summary Row */}
      <div className="intel-summary-row">
        <div className="intel-summary-item">
          <span className="intel-summary-label">Market Sentiment</span>
          <span className={sentimentClass}>{sentimentDisplay}</span>
        </div>
        <div className="intel-summary-item">
          <span className="intel-summary-label">Support Level</span>
          <span className="intel-summary-value">{structure.support.toLocaleString()}</span>
        </div>
        <div className="intel-summary-item">
          <span className="intel-summary-label">Resistance Level</span>
          <span className="intel-summary-value">{structure.resistance.toLocaleString()}</span>
        </div>
        <div className="intel-summary-item">
          <span className="intel-summary-label">Volatility Regime</span>
          <span className={regimeClass}>{volRegime.regime}</span>
        </div>
        <div className="intel-summary-item">
          <span className="intel-summary-label">Flow Pressure</span>
          <span className={pressureClass}>
            {flowPressure != null ? (flowPressure > 0 ? "Positive" : flowPressure < 0 ? "Negative" : "Neutral") : "N/A"}
          </span>
        </div>
      </div>

      {/* Detailed Intelligence Grid */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Market Intelligence</span>
        </div>
        <div className="intelligence-grid">
          {/* Market Structure */}
          <div className="intel-section">
            <h4 className="intel-section-title">Market Structure</h4>
            <div className="intel-row">
              <span className="intel-label">Support</span>
              <span className="intel-value">{structure.support.toLocaleString()}</span>
            </div>
            <div className="intel-row">
              <span className="intel-label">Support OI</span>
              <span className="intel-value-sm">{structure.support_oi.toLocaleString()}</span>
            </div>
            <div className="intel-row">
              <span className="intel-label">Resistance</span>
              <span className="intel-value">{structure.resistance.toLocaleString()}</span>
            </div>
            <div className="intel-row">
              <span className="intel-label">Resistance OI</span>
              <span className="intel-value-sm">{structure.resistance_oi.toLocaleString()}</span>
            </div>
            <div className="intel-row">
              <span className="intel-label">PCR</span>
              <span className="intel-value">{structure.pcr.toFixed(2)}</span>
            </div>
          </div>

          {/* Volatility Regime */}
          <div className="intel-section">
            <h4 className="intel-section-title">Volatility Regime</h4>
            <div className="intel-row">
              <span className="intel-label">Regime</span>
              <span className={`intel-badge ${
                volRegime.regime === "Expansion" ? "intel-badge-warn" :
                volRegime.regime === "Compression" ? "intel-badge-ok" : "intel-badge-neutral"
              }`}>{volRegime.regime}</span>
            </div>
            <div className="intel-row">
              <span className="intel-label">Mean IV</span>
              <span className="intel-value">{volRegime.mean_iv.toFixed(1)}%</span>
            </div>
            <div className="intel-row">
              <span className="intel-label">ATM IV</span>
              <span className="intel-value">{volRegime.atm_iv.toFixed(1)}%</span>
            </div>
            <div className="intel-row">
              <span className="intel-label">IV Std Dev</span>
              <span className="intel-value-sm">{volRegime.std_iv.toFixed(2)}%</span>
            </div>
          </div>

          {/* Unusual Activity */}
          <div className="intel-section">
            <h4 className="intel-section-title">Unusual Activity</h4>
            {!unusual.has_unusual_activity ? (
              <p className="intel-no-data">No unusual activity detected</p>
            ) : (
              unusual.alerts.slice(0, 5).map((alert, i) => (
                <div key={i} className="unusual-alert">
                  <div className="intel-row">
                    <span className="intel-label">Strike {alert.strike}</span>
                    <span className="intel-badge intel-badge-warn">{alert.type}</span>
                  </div>
                  <div className="intel-row">
                    <span className="intel-label-sm">Volume spike</span>
                    <span className="intel-value-sm">+{alert.pct_above_mean.toFixed(0)}%</span>
                  </div>
                  <div className="intel-row">
                    <span className="intel-label-sm">Z-Score</span>
                    <span className="intel-value-sm">{alert.z_score.toFixed(1)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </>
  );
}
