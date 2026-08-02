export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export type Event = { agent_name: string; status: string; message: string; timestamp: string };
export type Insight = { claim: string; evidence_field: string; evidence_value: number };
export type Status = { mission_id: string; stage: string; agent_status: Record<string, string>; error?: string; events: Event[] };
export type Results = { mission_id: string; stage: string; cleaned_data_summary: { original_rows?: number; cleaned_rows?: number; columns?: string[]; cleaning_log?: string[] }; charts_data: { top_categories: Record<string, Record<string, number>>; correlations: Record<string, Record<string, number>>; trend: { date_column?: string; metric?: string; points?: { period: string; value: number }[] } }; approved_insights: Insight[]; rejected_insights: { insight: Insight; reason: string }[] };
async function request<T>(path: string, init?: RequestInit): Promise<T> { const res = await fetch(`${API_URL}${path}`, init); if (!res.ok) throw new Error((await res.text()) || `Request failed (${res.status})`); return res.json(); }
export const getStatus = (id: string) => request<Status>(`/missions/${id}/status`, { cache: "no-store" });
export const getResults = (id: string) => request<Results>(`/missions/${id}/results`, { cache: "no-store" });
export const startSample = (goal?: string) => request<{ mission_id: string }>(`/sample-dataset${goal ? `?business_goal=${encodeURIComponent(goal)}` : ""}`);
export async function startUpload(file: File, goal?: string) { const body = new FormData(); body.append("file", file); if (goal) body.append("business_goal", goal); return request<{ mission_id: string }>("/missions", { method: "POST", body }); }
