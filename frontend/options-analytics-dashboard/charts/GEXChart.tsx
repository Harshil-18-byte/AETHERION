"use client";

import { useEffect, useRef } from "react";
import type { GEXByStrike } from "@/utils/types";

import { useTheme } from "next-themes";

interface GEXChartProps {
  data: GEXByStrike[];
  gammaFlipLevel: number | null;
  spot: number;
  loading?: boolean;
  error?: string;
}

export default function GEXChart({
  data,
  gammaFlipLevel,
  spot,
  loading,
  error,
}: GEXChartProps) {
  const { theme } = useTheme();
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current || data.length === 0) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    import("plotly.js-dist-min" as string).then((Plotly: any) => {
      if (!chartRef.current) return;

      const isDark = theme === "dark";
      const textColor = isDark ? "#F8FAFC" : "#1A1A1A";
      const secondaryColor = isDark ? "#94A3B8" : "#6B6B6B";
      const borderColor = isDark ? "#334155" : "#D9D9D9";
      const gridColor = isDark ? "#1E293B" : "#F0F0F0";
      const paperColor = isDark ? "#0F172A" : "#FFFFFF";

      const strikes = data.map((d) => d.strike);
      const netGex = data.map((d) => d.net_gex);
      const colors = netGex.map((v) =>
        v >= 0
          ? isDark
            ? "#38BDF8"
            : "#2C5AA0"
          : isDark
            ? "#F87171"
            : "#D94F4F",
      );

      const traces = [
        {
          x: strikes,
          y: netGex,
          type: "bar",
          marker: {
            color: colors,
            line: { width: 0 },
          },
          name: "Net GEX",
          hovertemplate: "Strike: %{x}<br>Net GEX: %{y:.4f}<extra></extra>",
        },
      ];

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const shapes: any[] = [];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const annotations: any[] = [];

      if (gammaFlipLevel) {
        shapes.push({
          type: "line",
          x0: gammaFlipLevel,
          x1: gammaFlipLevel,
          y0: 0,
          y1: 1,
          yref: "paper",
          line: { color: "#EAB308", width: 2, dash: "dot" },
        });
      }

      if (spot) {
        shapes.push({
          type: "line",
          x0: spot,
          x1: spot,
          y0: 0,
          y1: 1,
          yref: "paper",
          line: {
            color: isDark ? "rgba(255,255,255,0.4)" : "rgba(0,0,0,0.3)",
            width: 1,
            dash: "dash",
          },
        });
      }

      const layout = {
        font: { family: "Inter, sans-serif", size: 10, color: secondaryColor },
        xaxis: {
          title: {
            text: "Strike",
            font: { size: 10, color: secondaryColor },
            standoff: 8,
          },
          tickangle: -45,
          tickfont: { size: 9, color: secondaryColor },
          gridcolor: gridColor,
          linecolor: borderColor,
          fixedrange: true,
        },
        yaxis: {
          title: {
            text: "Net GEX (Cr)",
            font: { size: 10, color: secondaryColor },
            standoff: 12,
          },
          tickfont: { size: 9, color: secondaryColor },
          gridcolor: gridColor,
          zerolinecolor: borderColor,
          linecolor: borderColor,
          fixedrange: true,
        },
        shapes,
        annotations,
        margin: { l: 50, r: 10, t: 30, b: 40 },
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        showlegend: false,
        height: 380,
        hovermode: "closest",
        hoverlabel: {
          bgcolor: isDark ? "#1E293B" : "#FFFFFF",
          bordercolor: borderColor,
          font: { color: textColor, size: 11 },
        },
      };

      Plotly.newPlot(chartRef.current!, traces, layout, {
        responsive: true,
        displayModeBar: false,
        displaylogo: false,
      });
    });
  }, [data, gammaFlipLevel, spot, theme]);

  if (loading) {
    return (
      <div className="card">
        <div className="component-loading">
          <div className="component-loading-bar">
            <div className="component-loading-bar-inner" />
          </div>
          <span className="component-loading-text">
            Loading gamma exposure data...
          </span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="component-error">
          Unable to load gamma exposure data.
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div ref={chartRef} style={{ width: "100%", minHeight: 370 }} />
    </div>
  );
}
