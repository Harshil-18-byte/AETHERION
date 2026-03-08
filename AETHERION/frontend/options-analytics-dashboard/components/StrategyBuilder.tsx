"use client";

import React, { useState } from "react";
import ReactECharts from "echarts-for-react";

export default function StrategyBuilder() {
  const [legs, setLegs] = useState([
    { id: 1, type: "CALL", action: "BUY", strike: 25000, price: 150, qty: 1 },
    { id: 2, type: "CALL", action: "SELL", strike: 25500, price: 50, qty: 1 }
  ]);

  // Generate payoff data points
  const payoffData = [];
  const minStrike = Math.min(...legs.map(l => l.strike)) * 0.95;
  const maxStrike = Math.max(...legs.map(l => l.strike)) * 1.05;
  
  // Calculate Net Debit/Credit
  const netCost = legs.reduce((sum, leg) => {
    const cost = leg.price * leg.qty;
    return sum + (leg.action === "BUY" ? -cost : cost);
  }, 0);

  for (let s = minStrike; s <= maxStrike; s += 5) {
    let pnl = netCost; // Start with the net premium collected/paid
    for (const leg of legs) {
      if (leg.type === "CALL") {
        if (s > leg.strike) {
          const intrinsic = (s - leg.strike) * leg.qty;
          pnl += leg.action === "BUY" ? intrinsic : -intrinsic;
        }
      } else { // PUT
        if (s < leg.strike) {
          const intrinsic = (leg.strike - s) * leg.qty;
          pnl += leg.action === "BUY" ? intrinsic : -intrinsic;
        }
      }
    }
    payoffData.push([s, pnl]);
  }

  const options = {
    title: {
      text: "Strategy Payoff Simulator (Expiration)",
      left: "center",
      textStyle: { color: "var(--text)", fontSize: 12, fontWeight: "normal" }
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "var(--card-bg)",
      borderColor: "var(--border)",
      textStyle: { color: "var(--text)" },
      formatter: (params: any) => `Strike: ${params[0].value[0]}<br/>P/L: ₹${params[0].value[1]?.toFixed(2)}`
    },
    grid: { top: 40, left: 50, right: 30, bottom: 30 },
    xAxis: {
      type: "value",
      min: "dataMin",
      max: "dataMax",
      axisLabel: { color: "var(--text-secondary)" },
      splitLine: { show: false }
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "var(--text-secondary)" },
      splitLine: { lineStyle: { color: "var(--border-light)", type: "dashed" } }
    },
    series: [
      {
        type: "line",
        data: payoffData,
        smooth: false,
        symbol: "none",
        lineStyle: { width: 3 },
        itemStyle: { color: "#22c55e" },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: "rgba(34, 197, 94, 0.4)" }, { offset: 1, color: "rgba(34, 197, 94, 0.0)" }]
          }
        },
        markLine: {
          data: [{ yAxis: 0, lineStyle: { color: "var(--text-secondary)" } }]
        }
      }
    ]
  };

  return (
    <div className="strategy-panel">
      <div className="strategy-chart-area"><ReactECharts option={options} style={{ height: "100%", width: "100%" }} /></div>
      <div className="strategy-legs-area">
        <h4 className="strategy-legs-title">Simulated Legs (Bull Call Spread)</h4>
        <table className="strategy-table">
          <thead>
            <tr>
              <th>Action</th>
              <th>Type</th>
              <th>Strike</th>
              <th>Price</th>
              <th>Qty</th>
            </tr>
          </thead>
          <tbody>
            {legs.map(leg => (
              <tr key={leg.id}>
                <td className={leg.action === 'BUY' ? 'strategy-text-buy' : 'strategy-text-sell'}>{leg.action}</td>
                <td>{leg.type}</td>
                <td className="strategy-text-accent">{leg.strike}</td>
                <td>₹{leg.price}</td>
                <td>{leg.qty}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="strategy-net">
          <span className="strategy-net-label">Net Position: </span>
          <span className={netCost > 0 ? 'strategy-text-buy' : 'strategy-text-sell'}>
            {netCost > 0 ? `Credit ₹${netCost.toFixed(2)}` : `Debit ₹${Math.abs(netCost).toFixed(2)}`}
          </span>
        </div>
      </div>
    </div>
  );
}
