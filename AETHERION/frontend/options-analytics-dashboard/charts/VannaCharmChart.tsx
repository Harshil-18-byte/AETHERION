"use client";

import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import { useTheme } from "next-themes";
import type { VannaCharmItem } from "@/utils/types";

interface VannaCharmChartProps {
  data: VannaCharmItem[];
}

export default function VannaCharmChart({ data }: VannaCharmChartProps) {
  const { theme } = useTheme();

  const options = useMemo(() => {
    const sorted = [...data].sort((a, b) => a.strike - b.strike);
    const strikes = sorted.map((d) => d.strike.toString());
    const vanna = sorted.map((d) => d.vanna);
    const charm = sorted.map((d) => d.charm);

    const isDark = theme === 'dark';
    const textColor = isDark ? "#F8FAFC" : "#1A1A1A";
    const secondaryColor = isDark ? "#94A3B8" : "#6B6B6B";
    const borderColor = isDark ? "#334155" : "#D9D9D9";
    const tooltipBg = isDark ? "#1E293B" : "#FFFFFF";

    return {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        backgroundColor: tooltipBg,
        borderColor: borderColor,
        textStyle: { color: textColor, fontSize: 11 }
      },
      legend: {
        data: ["Vanna", "Charm"],
        bottom: 8,
        textStyle: { color: secondaryColor, fontSize: 10 }
      },
      grid: {
        top: 20,
        left: 50,
        right: 50,
        bottom: 50,
        containLabel: true
      },
      xAxis: {
        type: "category",
        data: strikes,
        axisLabel: { color: secondaryColor, fontSize: 10, rotate: 45 },
        splitLine: { show: false }
      },
      yAxis: [
        {
          type: "value",
          name: "Vanna",
          nameTextStyle: { color: secondaryColor, fontSize: 10, padding: [0, 0, 0, 20] },
          axisLabel: { color: secondaryColor, fontSize: 10 },
          splitLine: { lineStyle: { color: borderColor, type: "dashed" } },
          axisLine: { show: false },
          axisTick: { show: false }
        },
        {
          type: "value",
          name: "Charm",
          nameTextStyle: { color: secondaryColor, fontSize: 10, padding: [0, 20, 0, 0] },
          axisLabel: { color: secondaryColor, fontSize: 10 },
          splitLine: { show: false },
          axisLine: { show: false },
          axisTick: { show: false }
        }
      ],
      series: [
        {
          name: "Vanna",
          type: "line",
          data: vanna,
          smooth: true,
          itemStyle: { color: "#a855f7" }, // Purple
          areaStyle: {
            color: {
              type: "linear",
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: "rgba(168, 85, 247, 0.2)" }, { offset: 1, color: "rgba(168, 85, 247, 0.0)" }]
            }
          }
        },
        {
          name: "Charm",
          type: "line",
          yAxisIndex: 1,
          data: charm,
          smooth: true,
          itemStyle: { color: "#f59e0b" }, // Amber
          areaStyle: {
            color: {
              type: "linear",
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: "rgba(245, 158, 11, 0.2)" }, { offset: 1, color: "rgba(245, 158, 11, 0.0)" }]
            }
          }
        }
      ]
    };
  }, [data, theme]);

  return <ReactECharts option={options} style={{ height: "100%", width: "100%" }} theme={theme === "dark" ? "dark" : undefined} />;
}
