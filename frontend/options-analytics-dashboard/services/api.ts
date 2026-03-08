import axios from "axios";
import type { FullAnalysis } from "@/utils/types";

interface AnalysisResponse {
  expiries: string[];
  selected_expiry: string;
  analysis: FullAnalysis;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchAnalysis(expiry?: string): Promise<AnalysisResponse> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('optix_token') : null;
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const params = expiry ? `?expiry=${encodeURIComponent(expiry)}` : "";
  const res = await axios.get<AnalysisResponse>(`${API_BASE_URL}/analysis${params}`, { headers });
  return res.data;
}

export const fetcher = async (url: string) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('optix_token') : null;
  const headers: Record<string, string> = {};
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // If url is relative, prepend API_BASE_URL
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
  
  const res = await fetch(fullUrl, { headers });
  if (!res.ok) {
    if (res.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('optix_token');
      }
    }
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
};

export async function uploadAnalysis(file: File): Promise<AnalysisResponse> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('optix_token') : null;
  const headers: any = { "Content-Type": "multipart/form-data" };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const formData = new FormData();
  formData.append("file", file);
  const res = await axios.post<AnalysisResponse>(`${API_BASE_URL}/analysis`, formData, { headers });
  return res.data;
}
