import { NextRequest, NextResponse } from "next/server";
import Papa from "papaparse";
import { loadAllCSVs, getAvailableExpiries, getLatestSnapshot, getTimeSeries } from "@/utils/dataLoader";
import { runFullAnalysis } from "@/utils/analytics";
import type { OptionRow } from "@/utils/types";

let cachedData: ReturnType<typeof loadAllCSVs> | null = null;

function getData() {
  if (!cachedData) {
    cachedData = loadAllCSVs();
  }
  return cachedData;
}

export async function GET(request: NextRequest) {
  try {
    const data = getData();
    const url = new URL(request.url);
    const expiry = url.searchParams.get("expiry") || undefined;

    const expiries = getAvailableExpiries(data);
    const selectedExpiry = expiry || expiries[expiries.length - 1]; // default to latest

    const snapshot = getLatestSnapshot(data, selectedExpiry);
    const timeSeries = getTimeSeries(data, selectedExpiry);

    if (snapshot.length === 0) {
      return NextResponse.json({ error: "No data available" }, { status: 404 });
    }

    const analysis = runFullAnalysis(snapshot, timeSeries);

    return NextResponse.json({
      expiries,
      selected_expiry: selectedExpiry,
      analysis,
    });
  } catch (error) {
    console.error("Analysis API error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Internal server error" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("file") as File;
    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const text = await file.text();
    const result = Papa.parse<Record<string, string>>(text, { header: true, skipEmptyLines: true });

    const allRows: OptionRow[] = [];
    for (const raw of result.data) {
      allRows.push({
        symbol: raw.symbol || "UNKNOWN",
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

    allRows.sort((a, b) => {
      const dtCmp = a.datetime.localeCompare(b.datetime);
      return dtCmp !== 0 ? dtCmp : a.strike - b.strike;
    });

    const expiries = getAvailableExpiries(allRows);
    if (expiries.length === 0) {
      return NextResponse.json({ error: "Invalid CSV format or missing 'expiry' column." }, { status: 400 });
    }
    const selectedExpiry = expiries[expiries.length - 1]; // default to latest
    const snapshot = getLatestSnapshot(allRows, selectedExpiry);
    const timeSeries = getTimeSeries(allRows, selectedExpiry);

    if (snapshot.length === 0) {
      return NextResponse.json({ error: "No data available in CSV for analysis." }, { status: 404 });
    }

    const analysis = runFullAnalysis(snapshot, timeSeries);

    return NextResponse.json({
      expiries,
      selected_expiry: selectedExpiry,
      analysis,
    });
  } catch (error) {
    console.error("Custom CSV upload error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to parse custom dataset" },
      { status: 500 }
    );
  }
}
