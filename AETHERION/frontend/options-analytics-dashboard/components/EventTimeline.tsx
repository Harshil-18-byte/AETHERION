"use client";

import type { TimelineEvent } from "@/utils/types";

interface EventTimelineProps {
  events: TimelineEvent[];
  loading?: boolean;
  error?: string;
}

export default function EventTimeline({ events, loading, error }: EventTimelineProps) {
  const severityClass = (s: string) =>
    s === "high" ? "timeline-severity-high" : s === "medium" ? "timeline-severity-medium" : "timeline-severity-low";

  const severityLabelClass = (s: string) =>
    s === "high" ? "timeline-severity-label timeline-severity-label-high"
      : s === "medium" ? "timeline-severity-label timeline-severity-label-medium"
        : "timeline-severity-label timeline-severity-label-low";

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Market Events</span>
        <span className="card-badge">{events.length} Events</span>
      </div>
      {loading ? (
        <div className="component-loading">
          <div className="component-loading-bar">
            <div className="component-loading-bar-inner" />
          </div>
          <span className="component-loading-text">Loading market events...</span>
        </div>
      ) : error ? (
        <div className="component-error">Unable to load event timeline.</div>
      ) : (
        <div className="timeline-body">
          {events.length === 0 ? (
            <p className="timeline-empty">No significant events detected</p>
          ) : (
            <div className="timeline-list">
              {events.map((event, i) => (
                <div key={i} className="timeline-item">
                  <span className="timeline-time">{event.time}</span>
                  <span className={`timeline-dot ${severityClass(event.severity)}`} />
                  <div className="timeline-event-content">
                    <span className="timeline-event">{event.event}</span>
                    <span className={severityLabelClass(event.severity)}>
                      {event.severity}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
