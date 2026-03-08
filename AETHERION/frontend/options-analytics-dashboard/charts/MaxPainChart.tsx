"use client";

import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import { useTheme } from "next-themes";
import type { MaxPainResult, OptionRow } from "@/utils/types";

interface MaxPainChartProps {
  data: MaxPainResult;
  snapshot: OptionRow[];
}

export default function MaxPainChart({ data, snapshot }: MaxPainChartProps) {
  const { theme } = useTheme();

  const options = useMemo(() => {
    // Recalculate pain per strike for visualization
    const strikes = snapshot.map(r => r.strike).sort((a,b) => a-b);
    const painValues = strikes.map(targ => {
      let pain = 0;
      for (const opt of snapshot as any) {
        if(opt.strike < targ) pain += (opt.call_oi || 0) * (targ - opt.strike);
        if(opt.strike > targ) pain += (opt.put_oi || 0) * (opt.strike - targ);
      }
      return { value: pain, strike: targ };
    });

    const values = painValues.map(v => v.value);
    const strLabels = painValues.map(v => v.strike.toString());

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
      grid: {
        top: 20,
        left: 20,
        right: 20,
        bottom: 50,
        containLabel: true
      },
      xAxis: {
        type: "category",
        data: strLabels,
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
          name: "Total Value of Open Contracts",
          type: "bar",
          data: values,
          itemStyle: {
            color: (params: any) => {
              if (params.name === data.max_pain_strike.toString()) return "#22c55e"; // Theme Green
              return "#38bdf8"; // Theme Blue
            }
          }
        }
      ]
    };
  }, [data, snapshot, theme]);

  return <ReactECharts option={options} style={{ height: "100%", width: "100%" }} theme={theme === "dark" ? "dark" : undefined} />;
}
