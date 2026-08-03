"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Check, Circle, Loader2, X, type LucideIcon } from "lucide-react";
import { getStatus, Status } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

const agents = [
  { key: "data_engineer", label: "Data Engineer" }, { key: "eda_agent", label: "EDA Agent" },
  { key: "insight_agent", label: "Insight Agent" }, { key: "qa_agent", label: "QA Agent" },
];
type AgentPill = { label: string; className: string; Icon: LucideIcon };
function pill(status?: string): AgentPill {
  if (status === "complete" || status === "done") return { label: "done", className: "bg-emerald-100 text-emerald-700", Icon: Check };
  if (status === "running") return { label: "running", className: "bg-indigo-100 text-indigo-700", Icon: Loader2 };
  if (status === "failed" || status === "flagged") return { label: "flagged", className: "bg-red-100 text-red-700", Icon: X };
  return { label: "pending", className: "bg-slate-100 text-slate-600", Icon: Circle };
}

export default function WarRoom() {
  const { id } = useParams<{ id: string }>(); const router = useRouter();
  const [data, setData] = useState<Status>(); const [error, setError] = useState(""); const [slowStart, setSlowStart] = useState(false); const [attempts, setAttempts] = useState(0);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const next = await getStatus(id);
        if (!alive) return;
        setData(next); setSlowStart(false); setError("");
        if (next.stage === "complete" || next.stage === "completed") router.replace(`/mission/${id}/results`);
      } catch (e) {
        if (!alive) return;
        // Render's free tier spins down when idle; the first request(s) can take 30-50s to wake it.
        // Treat early failures as a cold start rather than a real error.
        setAttempts(a => { if (a < 4) { setSlowStart(true); } else { setError(e instanceof Error ? e.message : "Could not load mission."); } return a + 1; });
      }
    };
    load(); const timer = setInterval(load, 2000);
    return () => { alive = false; clearInterval(timer); };
  }, [id, router]);
  return <main className="mx-auto min-h-screen max-w-6xl px-6 py-12"><header className="mb-10"><p className="text-sm font-medium text-accent">InsightPilot AI / Mission</p><h1 className="mt-2 text-3xl font-semibold">Live War Room</h1><p className="mt-2 text-slate-500">Your specialist agents are working through the analysis.</p></header>{slowStart && !error && <p className="mb-6 text-sm text-slate-500">Waking up the analysis engine (free-tier backends nap when idle) — this can take up to a minute…</p>}{error && <p className="mb-6 text-red-600">{error}</p>}<div className="grid gap-6 lg:grid-cols-[0.9fr_1.4fr]"><Card><CardContent><h2 className="mb-6 font-semibold">Agent timeline</h2><ol className="space-y-6">{agents.map((agent, index) => { const { label, className, Icon } = pill(data?.agent_status?.[agent.key]); return <li key={agent.key} className="relative flex items-start gap-3">{index < agents.length - 1 && <span className="absolute left-3 top-7 h-8 border-l border-slate-200"/>}<span className="mt-0.5 grid h-6 w-6 place-items-center rounded-full border bg-white"><Icon size={13} className={label === "running" ? "animate-spin text-accent" : "text-slate-500"}/></span><div className="flex min-w-0 flex-1 items-center justify-between gap-3"><span className="font-medium">{agent.label}</span><Badge className={className}>{label}</Badge></div></li>; })}</ol></CardContent></Card><Card><CardContent><h2 className="mb-5 font-semibold">Event feed</h2><div className="max-h-[440px] space-y-4 overflow-y-auto pr-2">{data?.events?.length ? data.events.map((event, index) => <div key={`${event.timestamp}-${index}`} className="border-l-2 border-indigo-100 pl-4"><div className="flex items-center justify-between gap-3"><span className="text-sm font-medium">{event.agent_name.replace("_", " ")}</span><time className="text-xs text-slate-400">{new Date(event.timestamp).toLocaleTimeString()}</time></div><p className="mt-1 text-sm text-slate-500">{event.message}</p></div>) : <p className="text-sm text-slate-500">Waiting for the first agent update…</p>}</div></CardContent></Card></div></main>;
}
