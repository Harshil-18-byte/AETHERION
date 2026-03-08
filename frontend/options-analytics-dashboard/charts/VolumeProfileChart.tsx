"use client";

import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import { useTheme } from "next-themes";
import type { VolumeProfileResult } from "@/utils/types";

interface VolumeProfileChartProps {
  data: VolumeProfileResult;
}

export default function VolumeProfileChart({ data }: VolumeProfileChartProps) {
  const { theme } = useTheme();

  const options = useMemo(() => {
    const sorted = [...data.profile].sort((a, b) => a.strike - b.strike);
    const strikes = sorted.map((d) => d.strike.toString());
    const callVols = sorted.map((d) => d.call_volume);
    const putVols = sorted.map((d) => d.put_volume);

    const isDark = theme === 'dark';
    const textColor = isDark ? "#F8FAFC" : "#1A1A1A";
    const secondaryColor = isDark ? "#94A3B8" : "#6B6B6B";
    const borderColor = isDark ? "#334155" : "#D9D9D9";
    const tooltipBg = isDark ? "#1E293B" : "#FFFFFF";

    return {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: tooltipBg,
        borderColor: borderColor,
        textStyle: { color: textColor, fontSize: 11 }
      },
      legend: {
        data: ["Call Volume", "Put Volume"],
        bottom: 8,
        textStyle: { color: secondaryColor, fontSize: 10 }
      },
      grid: {
        top: 20,
        left: 10,
        right: 40,
        bottom: 50,
        containLabel: true
      },
      xAxis: {
        type: "value",
        axisLabel: { color: secondaryColor, fontSize: 10 },
        splitLine: { lineStyle: { color: borderColor, type: "dashed" } },
        axisLine: { show: false },
        axisTick: { show: false }
      },
      yAxis: {
        type: "category",
        data: strikes,
        axisLabel: { color: secondaryColor, fontSize: 10 },
        splitLine: { show: false }
      },
      series: [
        {
          name: "Call Volume",
          type: "bar",
          stack: "Total",
          data: callVols,
          itemStyle: { color: "rgba(56, 189, 248, 0.7)" } // Theme Blue
        },
        {
          name: "Put Volume",
          type: "bar",
          stack: "Total",
          data: putVols,
          itemStyle: { color: "rgba(248, 113, 113, 0.7)" }, // Theme Red
          markLine: {
            lineStyle: { type: "solid", color: "#eab308", width: 2 },
            label: { color: textColor, position: "end", formatter: "POC", fontSize: 10, fontWeight: "bold" },
            data: [{ yAxis: data.poc_strike.toString() }]
          }
        }
      ]
    };
  }, [data, theme]);

  return <ReactECharts option={options} style={{ height: "100%", width: "100%" }} theme={theme === "dark" ? "dark" : undefined} />;
}
