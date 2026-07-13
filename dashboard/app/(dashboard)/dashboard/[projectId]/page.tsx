"use client";

import { api, getMe } from "@/lib/api";
import { ArrowLeft, ExternalLink, Scan, Shield } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

interface Project {
  id: string; name: string; repo_url: string | null;
  github_owner: string | null; github_repo_name: string | null;
  vuln_counts: { critical: number; high: number; medium: number; low: number; info: number };
  last_scan_at: string | null; created_at: string;
}

interface ScanItem {
  id: string; status: string; trigger_type: string;
  files_scanned: number; total_findings: number;
  critical_count: number; high_count: number; medium_count: number; low_count: number;
  started_at: string | null; completed_at: string | null; created_at: string;
}

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [scans, setScans] = useState<ScanItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  const fetchData = useCallback(async () => {
    const [projRes, scanRes] = await Promise.all([
      api(`/v1/projects/${projectId}`),
      api(`/v1/projects/${projectId}/scans`),
    ]);
    if (!projRes.ok) { router.push("/dashboard"); return; }
    setProject(await projRes.json());
    if (scanRes.ok) {
      const data = await scanRes.json();
      setScans(data.scans || []);
    }
    setLoading(false);
  }, [projectId, router]);

  useEffect(() => {
    getMe().then((u) => {
      if (!u) { router.push("/login"); return; }
      fetchData();
    });
  }, [fetchData, router]);

  async function triggerScan() {
    setScanning(true);
    const res = await api(`/v1/projects/${projectId}/scans`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      // Poll for completion
      const poll = setInterval(async () => {
        const sr = await api(`/v1/scans/${data.scan_id}`);
        if (sr.ok) {
          const sd = await sr.json();
          if (sd.status === "completed" || sd.status === "failed") {
            clearInterval(poll);
            setScanning(false);
            fetchData();
          }
        }
      }, 3000);
    } else {
      setScanning(false);
    }
  }

  if (loading || !project) {
    return <div className="min-h-screen flex items-center justify-center text-text-secondary text-sm">Loading...</div>;
  }

  const counts = project.vuln_counts || { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  const lastScan = scans[0];

  return (
    <div className="min-h-screen bg-bg-base">
      <header className="border-b border-border-subtle">
        <div className="max-w-[1200px] mx-auto px-6 h-14 flex items-center gap-4">
          <Link href="/dashboard" className="text-text-tertiary hover:text-text-secondary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <Shield className="w-5 h-5 text-accent" />
          <span className="font-semibold tracking-tight">CIOTX</span>
        </div>
      </header>

      <main className="max-w-[1200px] mx-auto px-6 py-12">
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-2xl font-semibold tracking-tight">{project.name}</h1>
              {project.github_repo_name && (
                <a href={project.repo_url || "#"} target="_blank" rel="noopener noreferrer"
                   className="text-text-tertiary hover:text-text-secondary transition-colors">
                  <ExternalLink className="w-4 h-4" />
                </a>
              )}
            </div>
            <p className="text-text-secondary text-sm">
              {project.github_owner ? `${project.github_owner}/${project.github_repo_name}` : "Manual project"}
              {" · "}Created {new Date(project.created_at).toLocaleDateString()}
            </p>
          </div>
          <button onClick={triggerScan} disabled={scanning}
            className="flex items-center gap-2 bg-accent text-accent-text font-medium text-sm px-4 py-2.5 rounded-md hover:bg-accent-hover active:scale-[0.98] transition-all disabled:opacity-50">
            <Scan className="w-4 h-4" />
            {scanning ? "Scanning..." : "Scan Now"}
          </button>
        </div>

        <div className="grid grid-cols-5 gap-4 mb-8">
          {[
            { label: "Critical", count: counts.critical, color: "bg-severity-critical/10 text-severity-critical border-severity-critical/30" },
            { label: "High", count: counts.high, color: "bg-severity-high/10 text-severity-high border-severity-high/30" },
            { label: "Medium", count: counts.medium, color: "bg-severity-medium/10 text-severity-medium border-severity-medium/30" },
            { label: "Low", count: counts.low, color: "bg-severity-low/10 text-severity-low border-severity-low/30" },
            { label: "Info", count: counts.info, color: "bg-severity-info/10 text-severity-info border-severity-info/30" },
          ].map(({ label, count, color }) => (
            <div key={label} className={`border rounded-xl p-4 text-center ${color}`}>
              <div className="text-3xl font-semibold tabular-nums">{count}</div>
              <div className="text-xs mt-1 opacity-80">{label}</div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Scans</h2>
          {counts.critical + counts.high + counts.medium + counts.low + counts.info > 0 && (
            <Link href={`/dashboard/${projectId}/vulns`}
              className="text-sm text-text-secondary hover:text-text-primary transition-colors">
              View all vulnerabilities &rarr;
            </Link>
          )}
        </div>

        {scans.length === 0 ? (
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-12 flex flex-col items-center text-center">
            <div className="w-16 h-16 rounded-full bg-bg-hover flex items-center justify-center mb-6">
              <Scan className="w-8 h-8 text-text-tertiary" />
            </div>
            <h2 className="text-lg font-semibold mb-2">No scans yet</h2>
            <p className="text-text-secondary text-sm max-w-md">
              Run your first scan to find vulnerabilities in this project.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {scans.map((s) => (
              <Link key={s.id} href={`/dashboard/${projectId}/scans/${s.id}`}
                className="block bg-bg-surface border border-border-subtle rounded-lg hover:border-border-default transition-colors p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${
                        s.status === "completed" ? "bg-status-success/10 text-status-success" :
                        s.status === "failed" ? "bg-status-error/10 text-status-error" :
                        s.status === "queued" || s.status === "scanning" ? "bg-status-warning/10 text-status-warning" :
                        "bg-bg-hover text-text-secondary"
                      }`}>
                        {s.status}
                      </span>
                      <span className="text-xs text-text-tertiary">{s.trigger_type}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-secondary">
                      <span>{s.files_scanned} files</span>
                      <span>{s.total_findings} findings</span>
                      {s.critical_count > 0 && <span className="text-severity-critical">{s.critical_count} critical</span>}
                      {s.high_count > 0 && <span className="text-severity-high">{s.high_count} high</span>}
                      {s.medium_count > 0 && <span className="text-severity-medium">{s.medium_count} medium</span>}
                    </div>
                  </div>
                  <div className="text-xs text-text-tertiary">
                    {new Date(s.created_at).toLocaleString()}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
