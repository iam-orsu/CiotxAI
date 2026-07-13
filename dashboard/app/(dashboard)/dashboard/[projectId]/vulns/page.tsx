"use client";

import { api, getMe } from "@/lib/api";
import { ArrowLeft, Shield } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface Vuln {
  id: string; title: string; severity: string;
  cwe_id: string | null; cvss_score: number | null;
  file_path: string; line_start: number | null;
  status: string; confidence: number; created_at: string;
}

const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
const severityColors: Record<string, string> = {
  critical: "text-severity-critical bg-severity-critical/10 border-severity-critical/30",
  high: "text-severity-high bg-severity-high/10 border-severity-high/30",
  medium: "text-severity-medium bg-severity-medium/10 border-severity-medium/30",
  low: "text-severity-low bg-severity-low/10 border-severity-low/30",
  info: "text-severity-info bg-severity-info/10 border-severity-info/30",
};

export default function VulnListPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const [vulns, setVulns] = useState<Vuln[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sevFilter, setSevFilter] = useState("");

  useEffect(() => {
    getMe().then((u) => {
      if (!u) { router.push("/login"); return; }
      fetchVulns();
    });
  }, [projectId, router, sevFilter]);

  async function fetchVulns() {
    setLoading(true);
    const url = `/v1/projects/${projectId}/vulns?limit=100${sevFilter ? `&severity=${sevFilter}` : ""}`;
    const res = await api(url);
    if (res.ok) {
      const data = await res.json();
      setVulns(data.vulns || []);
      setTotal(data.total || 0);
    }
    setLoading(false);
  }

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
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight mb-1">Vulnerabilities</h1>
            <p className="text-text-secondary text-sm">{total} finding{total !== 1 ? "s" : ""}</p>
          </div>
          <div className="flex gap-2">
            {["", "critical", "high", "medium", "low"].map((s) => (
              <button key={s} onClick={() => setSevFilter(s)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  sevFilter === s
                    ? (severityColors[s] || "text-text-primary bg-bg-hover border-border-default")
                    : "text-text-secondary border-border-subtle hover:border-border-default"
                }`}>
                {s || "All"}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="text-text-secondary text-sm">Loading...</div>
        ) : vulns.length === 0 ? (
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-12 text-center">
            <p className="text-text-secondary">No vulnerabilities found.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {vulns.map((v) => {
              const sc = severityColors[v.severity] || severityColors.medium;
              return (
                <Link key={v.id} href={`/dashboard/${projectId}/vulns/${v.id}`}
                  className="block bg-bg-surface border border-border-subtle rounded-lg hover:border-border-default transition-colors p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium px-1.5 py-0.5 rounded border ${sc}`}>
                          {v.severity}
                        </span>
                        {v.cwe_id && <span className="text-xs text-text-tertiary">{v.cwe_id}</span>}
                      </div>
                      <h3 className="text-sm font-medium truncate">{v.title}</h3>
                      <div className="flex items-center gap-2 mt-1 text-xs text-text-tertiary">
                        <span className="font-mono">{v.file_path}</span>
                        {v.line_start && <span>L{v.line_start}</span>}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="text-xs text-text-tertiary">{(v.confidence * 100).toFixed(0)}% confidence</div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
