"use client";

import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import { useTheme } from "next-themes";

interface OIChartProps {
  data: { strike: number; call_oi: number; put_oi: number }[];
  loading?: boolean;
  error?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onEvents?: Record<string, (params: any) => void>;
}

export default function OIChart({ data, loading, error, onEvents }: OIChartProps) {
  const { theme } = useTheme();
  const options = useMemo(() => {
    if (data.length === 0) return {};

    const strikes = data.map(d => d.strike.toString());
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
        axisPointer: { type: "shadow" },
        backgroundColor: isDark ? "#1E293B" : "#FFFFFF",
        borderColor: borderColor,
        borderWidth: 1,
        textStyle: { color: textColor, fontSize: 11, fontFamily: "Inter, sans-serif" },
        formatter: (params: any[]) => {
          if (!params || params.length === 0) return "";
          let html = `<div style="font-weight:600;margin-bottom:4px;font-size:12px">Strike: ${params[0].name}</div>`;
          params.forEach(item => {
            html += `<div style="display:flex;justify-content:space-between;gap:20px;margin-bottom:2px">
              <span style="color:${item.color}">${item.seriesName}</span>
              <span style="font-weight:700;font-variant-numeric:tabular-nums">${item.value.toLocaleString()}</span>
            </div>`;
          });
          return html;
        },
      },
      legend: {
        data: ["Call OI", "Put OI"],
        bottom: 8,
        textStyle: { color: secondaryColor, fontSize: 10, fontFamily: "Inter, sans-serif" },
        itemWidth: 10,
        itemHeight: 10,
      },
      grid: { left: 50, right: 10, top: 20, bottom: 60, containLabel: true },
      xAxis: {
        type: "category",
        data: strikes,
        axisLabel: { rotate: 45, fontSize: 10, color: secondaryColor },
        axisLine: { lineStyle: { color: borderColor } },
        axisTick: { lineStyle: { color: borderColor } },
      },
      yAxis: {
        type: "value",
        axisLabel: { 
          formatter: (v: number) => (v / 1000).toFixed(0) + "K", 
          fontSize: 10, 
          color: secondaryColor 
        },
        splitLine: { lineStyle: { color: gridColor, type: "dashed" } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      dataZoom: [
        { type: "inside", xAxisIndex: 0, zoomOnMouseWheel: true, moveOnMouseMove: true },
      ],
      series: [
        { name: "Call OI", type: "bar", data: callOI, itemStyle: { color: isDark ? "#38BDF8" : "#2C5AA0" }, barMaxWidth: 12 },
        { name: "Put OI", type: "bar", data: putOI, itemStyle: { color: isDark ? "#F87171" : "#D94F4F" }, barMaxWidth: 12 },
      ],
    };
  }, [data, theme]);


  if (loading) {
    return (
      <div className="card">
        <div className="component-loading">
          <div className="component-loading-bar"><div className="component-loading-bar-inner" /></div>
          <span className="component-loading-text">Loading open interest data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="component-error">Unable to load open interest data.</div>
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
