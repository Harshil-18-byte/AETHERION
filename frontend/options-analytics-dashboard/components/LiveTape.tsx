"use client";

import React, { useState, useEffect } from "react";
import type { TapePrint } from "@/utils/types";

// Removed prints prop since it's now internal state via WebSocket
export default function LiveTape() {
  const [prints, setPrints] = useState<TapePrint[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Determine WS protocol based on window location (ws:// or wss://)
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // Assume backend is on port 8000 on the same host
    const wsHost = window.location.hostname === "localhost" ? "localhost:8000" : `${window.location.hostname}:8000`;
    const wsUrl = `${protocol}//${wsHost}/ws/tape`;
    
    let ws: WebSocket;
    
    const connect = () => {
      ws = new WebSocket(wsUrl);
      
      ws.onopen = () => setIsConnected(true);
      
      ws.onmessage = (event) => {
        try {
          const newPrints: TapePrint[] = JSON.parse(event.data);
          setPrints((prev) => {
            // Keep maximum of 100 prints in the UI
            const combined = [...newPrints, ...prev];
            return combined.slice(0, 100);
          });
        } catch (e) {
          console.error("Failed to parse tape message", e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt to reconnect after 3 seconds
        setTimeout(connect, 3000);
      };
      
      ws.onerror = (err) => {
        console.error("LiveTape WS error:", err);
        ws.close();
      };
    };

    connect();

    return () => {
      if (ws) ws.close();
    };
  }, []);

  return (
    <div className="flex flex-col h-full bg-[var(--card-bg)] border border-[var(--border)] overflow-hidden">
      <div className="flex items-center justify-between p-2 border-b border-[var(--border-light)] shrink-0">
        <div className="flex items-center gap-2">
           <span className="text-xs font-bold text-[var(--accent)] uppercase tracking-wider">Options Tape</span>
           <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} title={isConnected ? "Connected" : "Disconnected"} />
        </div>
        <span className="text-[10px] bg-[var(--accent-light)] text-[var(--accent)] px-2 py-0.5 border border-[var(--border)] uppercase font-semibold">Live</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {prints.length === 0 ? (
          <div className="text-xs text-[var(--text-muted)] text-center py-4">Waiting for live flow...</div>
        ) : (
          <table className="w-full text-left text-xs border-collapse">
            <thead className="sticky top-0 bg-[var(--card-bg)] border-b border-[var(--border-light)] z-10">
              <tr>
                <th className="py-2 pl-3 pr-2 font-semibold text-[var(--text-secondary)]">TIME</th>
                <th className="py-2 px-2 font-semibold text-[var(--text-secondary)]">CONTRACT</th>
                <th className="py-2 px-2 font-semibold text-[var(--text-secondary)] text-right">SIZE</th>
                <th className="py-2 px-2 font-semibold text-[var(--text-secondary)] text-right">PRICE</th>
                <th className="py-2 pr-3 pl-2 font-semibold text-[var(--text-secondary)] text-right">SENTIMENT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-light)]/50">
              {prints.map((p) => (
                <tr key={p.id} className="hover:bg-[var(--accent-light)] transition-colors animate-fade-in">
                  <td className="py-2 pl-3 pr-2 text-[10px] text-[var(--text-secondary)] font-mono whitespace-nowrap">
                    {p.time}
                  </td>
                  <td className={`py-2 px-2 font-bold whitespace-nowrap ${p.type === "CALL" ? "text-blue-400" : "text-red-400"}`}>
                    {p.strike} {p.type[0]}
                  </td>
                  <td className="py-2 px-2 text-[var(--text)] font-semibold text-right">
                    {p.size.toLocaleString()}
                  </td>
                  <td className="py-2 px-2 text-[var(--text)] font-mono text-right">
                    ₹{p.price.toFixed(2)}
                  </td>
                  <td className="py-2 pr-3 pl-2 text-right">
                    <span className={`text-[9px] px-1.5 py-0.5 inline-block uppercase border ${p.sentiment === 'BULLISH' ? 'border-green-500/30 text-green-400 bg-green-500/10' : 'border-red-500/30 text-red-400 bg-red-500/10'}`}>
                      {p.sentiment}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
