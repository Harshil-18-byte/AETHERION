"use client";

import React, { useState, useEffect } from "react";
import type { DarkPoolPrint } from "@/utils/types";

// Removed prints prop. Component manages its own socket state.
export default function DarkPoolFeed() {
  const [prints, setPrints] = useState<DarkPoolPrint[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsHost = window.location.hostname === "localhost" ? "localhost:8000" : `${window.location.hostname}:8000`;
    const wsUrl = `${protocol}//${wsHost}/ws/darkpool`;
    
    let ws: WebSocket;
    
    const connect = () => {
      ws = new WebSocket(wsUrl);
      
      ws.onopen = () => setIsConnected(true);
      
      ws.onmessage = (event) => {
        try {
          const newPrints: DarkPoolPrint[] = JSON.parse(event.data);
          setPrints((prev) => {
            // Keep maximum of 50 block prints
            const combined = [...newPrints, ...prev];
            return combined.slice(0, 50);
          });
        } catch (e) {
          console.error("Failed to parse dark pool message", e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        setTimeout(connect, 5000); // Reconnect interval 5s
      };
      
      ws.onerror = (err) => {
        console.error("DarkPoolFeed WS error:", err);
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
           <span className="text-xs font-bold text-[var(--accent)] uppercase tracking-wider">Dark Pool Block Prints</span>
           <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-purple-500 animate-pulse' : 'bg-red-500'}`} title={isConnected ? "Connected" : "Disconnected"} />
        </div>
        <span className="text-[10px] text-[var(--text-muted)] border border-[var(--border)] bg-[var(--card-bg)] px-2 uppercase font-semibold tracking-wide">Live Off-Exchange</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {prints.length === 0 ? (
          <div className="text-xs text-[var(--text-muted)] flex flex-col items-center justify-center h-full py-4 opacity-70">
            <span className="font-mono mb-2">Listening for Dark Pool blocks...</span>
          </div>
        ) : (
          <table className="w-full text-left text-xs border-collapse">
            <thead className="sticky top-0 bg-[var(--card-bg)] border-b border-[var(--border-light)] z-10">
              <tr>
                <th className="py-2 pl-3 pr-2 font-semibold text-[var(--text-secondary)]">TIME / ID</th>
                <th className="py-2 px-2 font-semibold text-[var(--text-secondary)] text-right">VOLUME</th>
                <th className="py-2 px-2 font-semibold text-[var(--text-secondary)] text-right">PRICE</th>
                <th className="py-2 pr-3 pl-2 font-semibold text-[var(--text-secondary)] text-right">EST. VALUE</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-light)]/50">
              {prints.map((p) => (
                <tr key={p.id} className="hover:bg-[var(--accent-light)] transition-colors animate-fade-in">
                  <td className="py-2 pl-3 pr-2 whitespace-nowrap">
                    <div className="flex flex-col">
                      <span className="text-[10px] text-[var(--text-secondary)] font-mono">{p.time}</span>
                      <span className="text-[9px] text-[var(--text-muted)] font-mono">{p.id}</span>
                    </div>
                  </td>
                  <td className="py-2 px-2 text-right">
                    <span className="text-[var(--text)] font-bold">{p.volume.toLocaleString()}</span>
                  </td>
                  <td className="py-2 px-2 text-right">
                    <span className="text-[var(--accent)] font-mono">₹{p.price.toFixed(2)}</span>
                  </td>
                  <td className="py-2 pr-3 pl-2 text-right">
                    <span className="text-purple-400 text-[10px] font-semibold border border-purple-500/30 bg-purple-500/10 px-1 inline-block uppercase">
                      ~₹{p.estimated_value}M
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
