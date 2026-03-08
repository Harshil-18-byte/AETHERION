/**
 * CSV Data Loader — Server-side utility for loading and preprocessing NIFTY options data.
 * Used by Next.js API routes.
 */

import fs from "fs";
import path from "path";
import Papa from "papaparse";
import type { OptionRow } from "./types";

const DATA_DIR = path.join(process.cwd(), "..", "..", "data");

export function loadAllCSVs(): OptionRow[] {
  const csvFiles = fs.readdirSync(DATA_DIR).filter(f => f.endsWith(".csv"));
  if (csvFiles.length === 0) throw new Error(`No CSV files found in ${DATA_DIR}`);

  const allRows: OptionRow[] = [];

  for (const file of csvFiles) {
    const content = fs.readFileSync(path.join(DATA_DIR, file), "utf-8");
    const result = Papa.parse<Record<string, string>>(content, { header: true, skipEmptyLines: true });

    for (const raw of result.data) {
      allRows.push({
        symbol: raw.symbol || "NIFTY",
        datetime: raw.datetime || "",
        expiry: raw.expiry || "",
        CE: parseFloat(raw.CE) || 0,
        PE: parseFloat(raw.PE) || 0,
        spot_close: parseFloat(raw.spot_close) || 0,
        ATM: parseFloat(raw.ATM) || 0,
        strike: parseFloat(raw.strike) || 0,
        oi_CE: parseFloat(raw.oi_CE) || 0,
        oi_PE: parseFloat(raw.oi_PE) || 0,
        volume_CE: parseFloat(raw.volume_CE) || 0,
        volume_PE: parseFloat(raw.volume_PE) || 0,
      });
    }
  }

  // Sort by datetime + strike
  allRows.sort((a, b) => {
    const dtCmp = a.datetime.localeCompare(b.datetime);
    return dtCmp !== 0 ? dtCmp : a.strike - b.strike;
  });

  return allRows;
}

export function getAvailableExpiries(data: OptionRow[]): string[] {
  const set = new Set(data.map(r => r.expiry));
  return [...set].sort();
}

export function getLatestSnapshot(data: OptionRow[], expiry?: string): OptionRow[] {
  const filtered = expiry ? data.filter(r => r.expiry === expiry) : data;
  if (filtered.length === 0) return [];

  // Find the latest timestamp
  const sorted = [...filtered].sort((a, b) => b.datetime.localeCompare(a.datetime));
  const latestTs = sorted[0].datetime;

  // Parse to get the cutoff time (30 min before latest)
  const latestDate = new Date(latestTs.replace(" ", "T"));
  const cutoff = new Date(latestDate.getTime() - 30 * 60 * 1000);
  const cutoffStr = cutoff.toISOString().replace("T", " ").slice(0, 19);

  const recent = filtered.filter(r => r.datetime >= cutoffStr);

  // Group by strike, keep latest per strike
  const byStrike = new Map<number, OptionRow>();
  for (const row of recent) {
    const existing = byStrike.get(row.strike);
    if (!existing || row.datetime > existing.datetime) {
      byStrike.set(row.strike, row);
    }
  }

  return [...byStrike.values()].sort((a, b) => a.strike - b.strike);
}

export function getTimeSeries(data: OptionRow[], expiry?: string): OptionRow[] {
  const filtered = expiry ? data.filter(r => r.expiry === expiry) : data;
  return [...filtered].sort((a, b) => {
    const dtCmp = a.datetime.localeCompare(b.datetime);
    return dtCmp !== 0 ? dtCmp : a.strike - b.strike;
  });
}
