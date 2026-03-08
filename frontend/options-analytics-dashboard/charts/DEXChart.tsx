"use client";

import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import { useTheme } from "next-themes";
import type { DeltaExposureItem } from "@/utils/types";

interface DEXChartProps {
  data: DeltaExposureItem[];
}

export default function DEXChart({ data }: DEXChartProps) {
  const { theme } = useTheme();

  const options = useMemo(() => {
    const sorted = [...data].sort((a, b) => a.strike - b.strike);
    const strikes = sorted.map((d) => d.strike.toString());
    const callDex = sorted.map((d) => d.call_dex);
    const putDex = sorted.map((d) => d.put_dex);

    const isDark = theme === 'dark';
    const textColor = isDark ? "#F8FAFC" : "#1A1A1A";
    const secondaryColor = isDark ? "#94A3B8" : "#6B6B6B";
    const borderColor = isDark ? "#334155" : "#D9D9D9";
    const tooltipBg = isDark ? "#1E293B" : "#FFFFFF";

    return {
      title: {
        textStyle: { color: textColor, fontSize: 12, fontWeight: "700" },
        show: false // Rely on panel header instead
      },
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: tooltipBg,
        borderColor: borderColor,
        textStyle: { color: textColor }
      },
      legend: {
        data: ["Call DEX", "Put DEX"],
        bottom: 10,
        textStyle: { color: secondaryColor, fontSize: 10 }
      },
      grid: {
        top: 20,
        left: 20,
        right: 20,
        bottom: 60,
        containLabel: true
      },
      xAxis: {
        type: "category",
        data: strikes,
        axisLabel: { color: secondaryColor, fontSize: 10, rotate: 45 },
        splitLine: { show: false }
      },
      yAxis: {
        type: "value",
        axisLabel: { color: secondaryColor, fontSize: 10 },
        splitLine: { lineStyle: { color: borderColor, type: "dashed" } },
        axisLine: { show: false },
        axisTick: { show: false }
      },
      series: [
        {
          name: "Call DEX",
          type: "bar",
          stack: "Total",
          data: callDex,
          itemStyle: { color: "#38bdf8" } // Theme Blue
        },
        {
          name: "Put DEX",
          type: "bar",
          stack: "Total",
          data: putDex,
          itemStyle: { color: "#f87171" } // Theme Red
        }
      ]
    };
  }, [data, theme]);

  return <ReactECharts option={options} style={{ height: "100%", width: "100%" }} theme={theme === "dark" ? "dark" : undefined} />;
}
