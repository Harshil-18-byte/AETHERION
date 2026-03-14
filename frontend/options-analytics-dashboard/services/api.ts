import axios from "axios";
import type { FullAnalysis } from "@/utils/types";

interface AnalysisResponse {
  expiries: string[];
  selected_expiry: string;
  analysis: FullAnalysis;
}

/*
Next.js client-side env vars must start with NEXT_PUBLIC_
Fallback to localhost for development
*/
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  "http://127.0.0.1:8000";

console.log(`[API] Base URL initialized as: ${API_BASE}`);

/*
Centralized Axios instance
*/
const API = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: {
    Accept: "application/json",
  },
});

/*
Retrieve auth token safely
*/
function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;

  return (
    localStorage.getItem("gammalens_token") ||
    localStorage.getItem("optix_token")
  );
}

/*
Attach token automatically
*/
API.interceptors.request.use((config) => {
  const token = getAuthToken();

  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

/*
========================
FETCH ANALYSIS
========================
*/

export async function fetchAnalysis(
  expiry?: string
): Promise<AnalysisResponse> {
  const params = expiry ? `?expiry=${encodeURIComponent(expiry)}` : "";
  const url = `/analysis${params}`;

  console.log(`[API] Calling backend: ${API_BASE}${url}`);

  try {
    const res = await API.get<AnalysisResponse>(url);

    console.log("[API] Analysis response received:", res.data);

    return res.data;
  } catch (err) {
    handleAxiosError(err, `${API_BASE}${url}`);
    throw err;
  }
}

/*
========================
GENERIC FETCHER (SWR)
========================
*/

export const fetcher = async (url: string) => {
  const fullUrl = url.startsWith("http") ? url : `${API_BASE}${url}`;

  console.log(`[API] Fetcher calling: ${fullUrl}`);

  try {
    const res = await API.get(url);

    return res.data;
  } catch (err) {
    handleAxiosError(err, fullUrl);
    throw err;
  }
};

/*
========================
UPLOAD ANALYSIS FILE
========================
*/

export async function uploadAnalysis(
  file: File
): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const url = `/analysis`;

  console.log(`[API] Uploading file to: ${API_BASE}${url}`);

  try {
    const res = await API.post<AnalysisResponse>(url, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return res.data;
  } catch (err) {
    handleAxiosError(err, `${API_BASE}${url}`);
    throw err;
  }
}

/*
========================
ERROR HANDLER
========================
*/

function handleAxiosError(err: unknown, url: string) {
  if (axios.isAxiosError(err)) {
    console.error(`[API] Error for ${url}:`, err.message);

    if (err.response) {
      const status = err.response.status;

      if (status === 503) {
        throw new Error(
          "Backend is warming up models. Please wait a few seconds and retry."
        );
      }

      if (status === 401) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("gammalens_token");
        }

        throw new Error(
          "Session expired. Please authenticate again."
        );
      }

      if (status === 405) {
        throw new Error(
          "Endpoint method not allowed. Check FastAPI route configuration."
        );
      }

      if (status === 500) {
        throw new Error(
          "Internal server error. Please check backend logs."
        );
      }

      throw new Error(
        `Server Error (${status}): ${
          err.response.data?.detail || err.message
        }`
      );
    }

    if (err.request) {
      throw new Error(
        `Network Error: Cannot reach backend at ${API_BASE}. Make sure FastAPI is running.`
      );
    }

    throw new Error(`Request configuration error: ${err.message}`);
  }

  console.error("[API] Unknown error:", err);
}