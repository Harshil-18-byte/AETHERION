"use client";

import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import { useTheme } from "next-themes";
import type { LiquidityItem } from "@/utils/types";

interface LiquidityHeatmapProps {
  data: LiquidityItem[];
  loading?: boolean;
  error?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onEvents?: Record<string, (params: any) => void>;
}

export default function LiquidityHeatmap({ data, loading, error, onEvents }: LiquidityHeatmapProps) {
  const { theme } = useTheme();
  const options = useMemo(() => {
    if (data.length === 0) return {};

    const strikes = data.map(d => d.strike.toString());
    const scores = data.map(d => d.liquidity_score);
    const callOI = data.map(d => d.call_oi);
    const putOI = data.map(d => d.put_oi);

    const isDark = theme === 'dark';
    const textColor = isDark ? "#F8FAFC" : "#1A1A1A";
    const secondaryColor = isDark ? "#94A3B8" : "#6B6B6B";
    const borderColor = isDark ? "#334155" : "#D9D9D9";
    const gridColor = isDark ? "#1E293B" : "#F0F0F0";

    return {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        backgroundColor: isDark ? "#1E293B" : "#FFFFFF",
        borderColor: borderColor,
        borderWidth: 1,
        textStyle: { color: textColor, fontSize: 11, fontFamily: "Inter, sans-serif" },
        formatter: (params: any[]) => {
          if (!params || !params[0]) return "";
          const idx = params[0].dataIndex;
          return `<div style="font-weight:600;margin-bottom:4px;font-size:12px">Strike: ${strikes[idx]}</div>` +
                 `<div style="display:flex;justify-content:space-between;gap:20px;margin-bottom:2px"><span>Liquidity Score</span><span style="font-weight:700">${scores[idx].toFixed(3)}</span></div>` +
                 `<div style="display:flex;justify-content:space-between;gap:20px"><span>Call OI</span><span style="font-weight:700;font-variant-numeric:tabular-nums">${callOI[idx].toLocaleString()}</span></div>` +
                 `<div style="display:flex;justify-content:space-between;gap:20px"><span>Put OI</span><span style="font-weight:700;font-variant-numeric:tabular-nums">${putOI[idx].toLocaleString()}</span></div>`;
        }
      },
      grid: { left: 50, right: 10, top: 20, bottom: 50, containLabel: true },
      xAxis: {
        type: "category",
        data: strikes,
        axisLabel: { rotate: 45, fontSize: 10, color: secondaryColor },
        axisLine: { lineStyle: { color: borderColor } },
        axisTick: { lineStyle: { color: borderColor } },
      },
      yAxis: {
        type: "value",
        name: "Score",
        max: 1,
        nameTextStyle: { color: secondaryColor, fontSize: 10, padding: [0, 0, 0, 20] },
        axisLabel: { fontSize: 10, color: secondaryColor },
        splitLine: { lineStyle: { color: gridColor, type: "dashed" } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      dataZoom: [
        { type: "inside", xAxisIndex: 0, zoomOnMouseWheel: true, moveOnMouseMove: true },
      ],
      series: [{
        type: "bar",
        data: scores.map((s) => ({ value: s, itemStyle: { color: getColor(s, isDark) } })),
        barMaxWidth: 12,
      }],
    };
  }, [data, theme]);

  if (loading) {
    return (
      <div className="card">
        <div className="component-loading">
          <div className="component-loading-bar"><div className="component-loading-bar-inner" /></div>
          <span className="component-loading-text">Loading liquidity data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="component-error">Unable to load liquidity data.</div>
      </div>
    );
  }

  return (
    <div className="card" style={{ height: "100%", padding: 0, border: "none" }}>
      {data.length > 0 && (
        <ReactECharts
          option={options}
          style={{ height: "100%", width: "100%", minHeight: 300 }}
          theme={theme === "dark" ? "dark" : undefined}
          onEvents={onEvents}
          opts={{ renderer: "canvas" }}
          notMerge={false}
          lazyUpdate={true}
        />
      )}
    </div>
  );
}

function getColor(score: number, isDark: boolean): string {
  if (isDark) {
    if (score > 0.8) return "#38BDF8";
    if (score > 0.6) return "#0EA5E9";
    if (score > 0.4) return "#0284C7";
    if (score > 0.2) return "#075985";
    return "#1E293B";
  }
  if (score > 0.8) return "#1A3D7A";
  if (score > 0.6) return "#2C5AA0";
  if (score > 0.4) return "#6A93C4";
  if (score > 0.2) return "#B0C4DE";
  return "#E0E0E0";
}
