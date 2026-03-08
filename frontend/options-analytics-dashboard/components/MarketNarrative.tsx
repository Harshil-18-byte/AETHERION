"use client";

interface MarketNarrativeProps {
  narrative: string;
  loading?: boolean;
  error?: string;
}

export default function MarketNarrative({ narrative, loading, error }: MarketNarrativeProps) {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Market Narrative</span>
        <span className="card-badge">AI Generated</span>
      </div>
      {loading ? (
        <div className="component-loading">
          <div className="component-loading-bar">
            <div className="component-loading-bar-inner" />
          </div>
          <span className="component-loading-text">Generating market narrative...</span>
        </div>
      ) : error ? (
        <div className="component-error">Unable to generate market narrative.</div>
      ) : (
        <div className="narrative-body">
          <span className="narrative-label">Analysis Summary</span>
          <p className="narrative-text">{narrative}</p>
        </div>
      )}
    </div>
  );
}
