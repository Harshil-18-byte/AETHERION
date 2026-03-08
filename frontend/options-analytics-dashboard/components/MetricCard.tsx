"use client";

interface MetricCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  accent?: boolean;
  sentiment?: "positive" | "negative" | "neutral";
  loading?: boolean;
  error?: string;
}

export default function MetricCard({ label, value, subtitle, accent, sentiment, loading, error }: MetricCardProps) {
  if (loading) {
    return (
      <div className={`metric-card ${accent ? "metric-card-accent" : ""}`}>
        <span className="metric-label">{label}</span>
        <div className="component-loading" style={{ padding: "8px 0" }}>
          <div className="component-loading-bar">
            <div className="component-loading-bar-inner" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`metric-card ${accent ? "metric-card-accent" : ""}`}>
        <span className="metric-label">{label}</span>
        <span className="metric-value" style={{ color: "var(--red)", fontSize: 12 }}>Error</span>
      </div>
    );
  }

  const subtitleClass = sentiment === "positive"
    ? "metric-subtitle metric-subtitle-positive"
    : sentiment === "negative"
      ? "metric-subtitle metric-subtitle-negative"
      : "metric-subtitle";

  return (
    <div className={`metric-card ${accent ? "metric-card-accent" : ""}`}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
      {subtitle && <span className={subtitleClass}>{subtitle}</span>}
    </div>
  );
}
