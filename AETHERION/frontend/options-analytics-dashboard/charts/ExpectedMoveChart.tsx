"use client";

import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { ExpectedMoveResult } from "@/utils/types";

interface ExpectedMoveChartProps {
  data: ExpectedMoveResult;
  spot: number;
}

export default function ExpectedMoveChart({ data, spot }: ExpectedMoveChartProps) {
  const options = useMemo(() => {
    return {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        backgroundColor: "var(--card-bg)",
        borderColor: "var(--border)",
        textStyle: { color: "var(--text)", fontSize: 11 }
      },
      legend: {
        data: ["Current Spot", "Daily EM", "Weekly EM", "Monthly EM"],
        bottom: 8,
        textStyle: { color: "var(--text-secondary)", fontSize: 10 }
      },
      grid: {
        top: 20,
        left: 20,
        right: 40,
        bottom: 50,
        containLabel: true
      },
      xAxis: {
        type: "value",
        min: spot - data.monthly * 1.5,
        max: spot + data.monthly * 1.5,
        axisLabel: { color: "var(--text-secondary)", fontSize: 10 },
        splitLine: { show: true, lineStyle: { color: "var(--border)", type: "dashed" } }
      },
      yAxis: {
        type: "category",
        data: ["Monthly EM", "Weekly EM", "Daily EM"],
        axisLabel: { color: "var(--text-secondary)", fontSize: 10 },
        splitLine: { show: false }
      },
      series: [
        {
          name: "Current Spot",
          type: "scatter",
          symbolSize: 8,
          itemStyle: { color: "var(--accent)" },
          data: [ [spot, "Monthly EM"], [spot, "Weekly EM"], [spot, "Daily EM"] ],
          markArea: {
            itemStyle: { opacity: 0.12 },
            label: { show: false },
            data: [
              [
                { xAxis: spot - data.monthly, yAxis: "Monthly EM", itemStyle: { color: "#f87171" } },
                { xAxis: spot + data.monthly, yAxis: "Monthly EM" }
              ],
              [
                { xAxis: spot - data.weekly, yAxis: "Weekly EM", itemStyle: { color: "#a855f7" } },
                { xAxis: spot + data.weekly, yAxis: "Weekly EM" }
              ],
              [
                { xAxis: spot - data.daily, yAxis: "Daily EM", itemStyle: { color: "#38bdf8" } },
                { xAxis: spot + data.daily, yAxis: "Daily EM" }
              ]
            ]
          }
        }
      ]
    };
  }, [data, spot]);

  return <ReactECharts option={options} style={{ height: "100%", width: "100%" }} />;
}
