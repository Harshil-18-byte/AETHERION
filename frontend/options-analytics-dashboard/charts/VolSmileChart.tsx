"use client";

import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import * as echarts from "echarts";
import { useTheme } from "next-themes";
import type { IVByStrike } from "@/utils/types";

interface VolSmileChartProps {
  data: IVByStrike[];
  spot: number;
  loading?: boolean;
  error?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onEvents?: Record<string, (params: any) => void>;
}

export default function VolSmileChart({ data, spot, loading, error, onEvents }: VolSmileChartProps) {
  const { theme } = useTheme();
  const options = useMemo(() => {
    if (data.length === 0) return {};

    const filtered = data.filter(d => d.iv > 0);
    const strikes = filtered.map(d => d.strike);
    const ivs = filtered.map(d => d.iv);

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
          return `<div style="font-weight:600;margin-bottom:4px;font-size:12px">Strike: ${params[0].name}</div>` +
                 `<div style="display:flex;justify-content:space-between;gap:20px"><span>Implied Vol</span><span style="font-weight:700;color:${isDark ? "#38BDF8" : "#2C5AA0"}">${params[0].value.toFixed(2)}%</span></div>`;
        }
      },
      grid: { left: 50, right: 20, top: 20, bottom: 50, containLabel: true },
      xAxis: {
        type: "category",
        data: strikes.map(s => s.toString()),
        axisLabel: { rotate: 45, fontSize: 10, color: secondaryColor },
        axisLine: { lineStyle: { color: borderColor } },
        axisTick: { lineStyle: { color: borderColor } },
      },
      yAxis: {
        type: "value",
        name: "IV (%)",
        nameTextStyle: { color: secondaryColor, fontSize: 10, padding: [0, 0, 0, 20] },
        axisLabel: { formatter: (v: number) => v.toFixed(0) + "%", fontSize: 10, color: secondaryColor },
        splitLine: { lineStyle: { color: gridColor, type: "dashed" } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      dataZoom: [
        { type: "inside", xAxisIndex: 0, zoomOnMouseWheel: true, moveOnMouseMove: true },
      ],
      series: [{
        type: "line",
        data: ivs,
        smooth: true,
        lineStyle: { color: isDark ? "#38BDF8" : "#2C5AA0", width: 2.5 },
        areaStyle: { 
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: isDark ? "rgba(56, 189, 248, 0.2)" : "rgba(44, 90, 160, 0.2)" },
            { offset: 1, color: "transparent" }
          ])
        },
        itemStyle: { color: isDark ? "#38BDF8" : "#2C5AA0" },
        symbolSize: 4,
        markLine: spot ? {
          silent: true,
          symbol: "none",
          data: [{ 
            xAxis: spot.toString(), 
            label: { formatter: "SPOT", position: "end", fontSize: 9, fontWeight: "bold", color: isDark ? "#F8FAFC" : "#1A1A1A" }, 
            lineStyle: { color: isDark ? "rgba(255,255,255,0.4)" : "rgba(0,0,0,0.3)", type: "dashed", width: 1 } 
          }],
        } : undefined,
      }],
    };
  }, [data, spot, theme]);

  if (loading) {
    return (
      <div className="card">
        <div className="component-loading">
          <div className="component-loading-bar"><div className="component-loading-bar-inner" /></div>
          <span className="component-loading-text">Loading volatility data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="component-error">Unable to load volatility data.</div>
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
