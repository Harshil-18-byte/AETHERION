import axios from "axios";
import type { FullAnalysis } from "@/utils/types";

interface AnalysisResponse {
  expiries: string[];
  selected_expiry: string;
  analysis: FullAnalysis;
}

export async function fetchAnalysis(expiry?: string): Promise<AnalysisResponse> {
  const params = expiry ? `?expiry=${encodeURIComponent(expiry)}` : "";
  const res = await axios.get<AnalysisResponse>(`/api/analysis${params}`);
  return res.data;
}
export async function uploadAnalysis(file: File): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await axios.post<AnalysisResponse>(`/api/analysis`, formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return res.data;
}
