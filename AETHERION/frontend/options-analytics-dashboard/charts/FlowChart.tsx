import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import { useTheme } from "next-themes";
import { FlowByStrike } from "@/utils/types";

interface FlowChartProps {
  data: FlowByStrike[];
  loading?: boolean;
  error?: string | null;
  onEvents?: Record<string, (params: any) => void>;
}

export default function FlowChart({ data, loading, error, onEvents }: FlowChartProps) {
  const { theme } = useTheme();
  const options = useMemo(() => {
    if (data.length === 0) return {};

    const strikes = data.map(d => d.strike.toString());
    const pressures = data.map(d => d.strike_pressure);

    const isDark = theme === 'dark';
    const textColor = isDark ? "#F8FAFC" : "#1A1A1A";
    const secondaryColor = isDark ? "#94A3B8" : "#6B6B6B";
    const borderColor = isDark ? "#334155" : "#D9D9D9";
    const gridColor = isDark ? "#1E293B" : "#F0F0F0";

    const getColor = (val: number, isDark: boolean) => {
      if (val > 0) return isDark ? "#22C55E" : "#3D8B37";
      return isDark ? "#EF4444" : "#D94F4F";
    };

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
          if (!params || !params[0]) return "";
          const val = params[0].value;
          const typeStr = val > 0 ? "Call Dominated" : "Put Dominated";
          return `<div style="font-weight:600;margin-bottom:4px;font-size:12px">Strike: ${params[0].name}</div>` +
                 `<div style="display:flex;justify-content:space-between;gap:20px"><span>Pressure</span><span style="font-weight:700;color:${getColor(val, isDark)}">${val.toFixed(2)}</span></div>` +
                 `<div style="font-size:10px;color:${secondaryColor};margin-top:2px">${typeStr}</div>`;
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
        name: "Pressure",
        nameTextStyle: { color: secondaryColor, fontSize: 10, padding: [0, 0, 0, 40] },
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
        data: pressures.map((p) => ({ value: p, itemStyle: { color: getColor(p, isDark) } })),
        barMaxWidth: 12,
      }],
    };
  }, [data, theme]);

  if (loading) {
    return (
      <div className="card">
        <div className="component-loading">
          <div className="component-loading-bar"><div className="component-loading-bar-inner" /></div>
          <span className="component-loading-text">Loading flow data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="component-error">Unable to load flow data.</div>
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
