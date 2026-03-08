"use client";

import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { VolConesResult } from "@/utils/types";

interface VolConesChartProps {
  data: VolConesResult;
}

export default function VolConesChart({ data }: VolConesChartProps) {
  const options = useMemo(() => {
    return {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: "var(--card-bg)",
        borderColor: "var(--border)",
        textStyle: { color: "var(--text)", fontSize: 11 }
      },
      grid: {
        top: 20,
        left: 20,
        right: 20,
        bottom: 20,
        containLabel: true
      },
      xAxis: {
        type: "value",
        min: 0,
        max: Math.max(data.iv_percentile_90, data.current_iv) + 5,
        axisLabel: { color: "var(--text-secondary)", fontSize: 10 },
        splitLine: { show: true, lineStyle: { color: "var(--border)", type: "dashed" } }
      },
      yAxis: {
        type: "category",
        data: ["Volatility"],
        axisLabel: { show: false },
        splitLine: { show: false }
      },
      series: [
        {
          name: "50th Percentile (Historical Median)",
          type: "scatter",
          symbol: "rect",
          symbolSize: [3, 40],
          itemStyle: { color: "var(--text-muted)" },
          data: [[data.iv_percentile_50, "Volatility"]],
          markArea: {
            itemStyle: { color: "var(--bg)", opacity: 0.5 },
            label: { show: false },
            data: [ [ { xAxis: data.iv_percentile_10 }, { xAxis: data.iv_percentile_90 } ] ]
          }
        },
        {
          name: "Current IV",
          type: "scatter",
          symbol: "triangle",
          symbolSize: 12,
          itemStyle: { color: "var(--green)" },
          data: [[data.current_iv, "Volatility"]]
        }
      ]
    };
  }, [data]);

  return <ReactECharts option={options} style={{ height: "100%", width: "100%" }} />;
}
