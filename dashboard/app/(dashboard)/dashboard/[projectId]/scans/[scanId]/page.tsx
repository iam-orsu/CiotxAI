"use client";

import { api, getMe } from "@/lib/api";
import { ArrowLeft, Shield } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface ScanDetail {
  id: string; project_id: string; status: string;
  trigger_type: string; branch: string | null; commit_sha: string | null;
  files_scanned: number; total_findings: number;
  critical_count: number; high_count: number; medium_count: number; low_count: number;
  total_cost_cents: number;
  started_at: string | null; completed_at: string | null; created_at: string;
  agents: { name: string; status: string; input_tokens: number; output_tokens: number; cost_cents: number; findings_count: number; error_message: string | null }[];
}

export default function ScanDetailPage() {
  const { projectId, scanId } = useParams<{ projectId: string; scanId: string }>();
  const router = useRouter();
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe().then((u) => {
      if (!u) { router.push("/login"); return; }
      api(`/v1/scans/${scanId}`).then(async (res) => {
        if (!res.ok) { router.push(`/dashboard/${projectId}`); return; }
        setScan(await res.json());
        setLoading(false);
      });
    });
  }, [projectId, scanId, router]);

  if (loading || !scan) {
    return <div className="min-h-screen flex items-center justify-center text-text-secondary text-sm">Loading...</div>;
  }

  const duration = scan.started_at && scan.completed_at
    ? Math.round((new Date(scan.completed_at).getTime() - new Date(scan.started_at).getTime()) / 1000)
    : null;

  return (
    <div className="min-h-screen bg-bg-base">
      <header className="border-b border-border-subtle">
        <div className="max-w-[1200px] mx-auto px-6 h-14 flex items-center gap-4">
          <Link href={`/dashboard/${projectId}`} className="text-text-tertiary hover:text-text-secondary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <Shield className="w-5 h-5 text-accent" />
          <span className="font-semibold tracking-tight">CIOTX</span>
        </div>
      </header>

      <main className="max-w-[1200px] mx-auto px-6 py-12">
        <Link href={`/dashboard/${projectId}`} className="text-text-secondary text-sm hover:text-text-primary transition-colors mb-4 inline-block">
          &larr; Back to project
        </Link>

        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                scan.status === "completed" ? "bg-status-success/10 text-status-success" :
                scan.status === "failed" ? "bg-status-error/10 text-status-error" :
                "bg-status-warning/10 text-status-warning"
              }`}>
                {scan.status}
              </span>
              <span className="text-xs text-text-tertiary">{scan.trigger_type}</span>
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">Scan {scan.id.slice(0, 8)}</h1>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-4 text-center">
            <div className="text-2xl font-semibold tabular-nums">{scan.files_scanned}</div>
            <div className="text-xs text-text-secondary mt-1">Files scanned</div>
          </div>
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-4 text-center">
            <div className="text-2xl font-semibold tabular-nums">{scan.total_findings}</div>
            <div className="text-xs text-text-secondary mt-1">Findings</div>
          </div>
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-4 text-center">
            <div className="text-2xl font-semibold tabular-nums">{duration ? `${duration}s` : "—"}</div>
            <div className="text-xs text-text-secondary mt-1">Duration</div>
          </div>
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-4 text-center">
            <div className="text-2xl font-semibold tabular-nums">${(scan.total_cost_cents / 100).toFixed(4)}</div>
            <div className="text-xs text-text-secondary mt-1">Cost</div>
          </div>
        </div>

        <div className="grid grid-cols-5 gap-4 mb-8">
          {[
            { label: "Critical", count: scan.critical_count, color: "text-severity-critical" },
            { label: "High", count: scan.high_count, color: "text-severity-high" },
            { label: "Medium", count: scan.medium_count, color: "text-severity-medium" },
            { label: "Low", count: scan.low_count, color: "text-severity-low" },
            { label: "Info", count: 0, color: "text-text-tertiary" },
          ].map(({ label, count, color }) => (
            <div key={label} className="bg-bg-surface border border-border-subtle rounded-xl p-4 text-center">
              <div className={`text-2xl font-semibold tabular-nums ${color}`}>{count}</div>
              <div className="text-xs text-text-secondary mt-1">{label}</div>
            </div>
          ))}
        </div>

        {scan.agents.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-text-secondary mb-3">Agents</h3>
            <div className="space-y-2">
              {scan.agents.map((a, i) => (
                <div key={i} className="bg-bg-surface border border-border-subtle rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-sm font-medium">{a.name}</span>
                      <span className={`text-xs ml-2 px-1.5 py-0.5 rounded-full ${
                        a.status === "completed" ? "bg-status-success/10 text-status-success" :
                        a.status === "failed" ? "bg-status-error/10 text-status-error" :
                        "bg-status-warning/10 text-status-warning"
                      }`}>{a.status}</span>
                    </div>
                    <div className="text-xs text-text-tertiary">
                      {a.input_tokens.toLocaleString()} in / {a.output_tokens.toLocaleString()} out / ${(a.cost_cents / 100).toFixed(4)} / {a.findings_count} findings
                    </div>
                  </div>
                  {a.error_message && (
                    <div className="mt-2 text-xs text-severity-critical bg-severity-critical/5 rounded p-2 font-mono">{a.error_message}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
