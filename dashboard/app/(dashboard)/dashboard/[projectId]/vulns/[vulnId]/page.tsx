"use client";

import { api, getMe } from "@/lib/api";
import { ArrowLeft, Copy, ExternalLink, Shield } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface Vuln {
  id: string; scan_id: string; project_id: string;
  title: string; description: string | null;
  severity: string; cwe_id: string | null; cvss_score: number | null;
  file_path: string; line_start: number | null; line_end: number | null;
  vulnerable_code: string | null; fix_suggestion: string | null; fix_diff: string | null;
  status: string; source_agent: string | null; confidence: number;
  created_at: string;
}

const severityColors: Record<string, string> = {
  critical: "bg-severity-critical/10 text-severity-critical border-severity-critical/30",
  high: "bg-severity-high/10 text-severity-high border-severity-high/30",
  medium: "bg-severity-medium/10 text-severity-medium border-severity-medium/30",
  low: "bg-severity-low/10 text-severity-low border-severity-low/30",
  info: "bg-severity-info/10 text-severity-info border-severity-info/30",
};

export default function VulnDetailPage() {
  const { projectId, vulnId } = useParams<{ projectId: string; vulnId: string }>();
  const router = useRouter();
  const [vuln, setVuln] = useState<Vuln | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    getMe().then((u) => {
      if (!u) { router.push("/login"); return; }
      api(`/v1/vulns/${vulnId}`).then(async (res) => {
        if (!res.ok) { router.push(`/dashboard/${projectId}`); return; }
        setVuln(await res.json());
        setLoading(false);
      });
    });
  }, [projectId, vulnId, router]);

  async function copyFix() {
    if (vuln?.fix_diff) {
      await navigator.clipboard.writeText(vuln.fix_diff);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  if (loading || !vuln) {
    return <div className="min-h-screen flex items-center justify-center text-text-secondary text-sm">Loading...</div>;
  }

  const color = severityColors[vuln.severity] || severityColors.medium;

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

        <div className="flex items-start justify-between mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className={`text-xs font-medium px-2 py-0.5 rounded border ${color}`}>
                {vuln.severity.toUpperCase()}
              </span>
              {vuln.cwe_id && (
                <a href={`https://cwe.mitre.org/data/definitions/${vuln.cwe_id.replace('CWE-','')}.html`}
                   target="_blank" rel="noopener noreferrer"
                   className="text-xs text-text-tertiary hover:text-text-secondary transition-colors flex items-center gap-1">
                  {vuln.cwe_id} <ExternalLink className="w-3 h-3" />
                </a>
              )}
              {vuln.cvss_score && (
                <span className="text-xs text-text-tertiary">CVSS {vuln.cvss_score}</span>
              )}
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">{vuln.title}</h1>
          </div>
          <div className="text-right">
            <div className="text-sm text-text-secondary">Confidence</div>
            <div className="text-lg font-semibold tabular-nums">{(vuln.confidence * 100).toFixed(0)}%</div>
          </div>
        </div>

        {vuln.description && (
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-6 mb-6">
            <h3 className="text-sm font-medium text-text-secondary mb-2">Description</h3>
            <p className="text-sm leading-relaxed">{vuln.description}</p>
          </div>
        )}

        {vuln.vulnerable_code && (
          <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden mb-6">
            <div className="flex items-center justify-between px-4 py-2 bg-bg-hover border-b border-border-subtle">
              <div className="flex items-center gap-2 text-xs text-text-secondary">
                <span>{vuln.file_path}</span>
                {vuln.line_start && <span>L{vuln.line_start}{vuln.line_end ? `-L${vuln.line_end}` : ""}</span>}
              </div>
            </div>
            <pre className="p-4 overflow-x-auto text-sm font-mono leading-relaxed">
              <code className={`${vuln.severity === "critical" ? "text-severity-critical" : vuln.severity === "high" ? "text-severity-high" : "text-severity-medium"}`}>
                {vuln.vulnerable_code}
              </code>
            </pre>
          </div>
        )}

        {vuln.fix_suggestion && (
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-6 mb-6">
            <h3 className="text-sm font-medium text-text-secondary mb-2">Fix Suggestion</h3>
            <p className="text-sm leading-relaxed">{vuln.fix_suggestion}</p>
          </div>
        )}

        {vuln.fix_diff && (
          <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden mb-6">
            <div className="flex items-center justify-between px-4 py-2 bg-bg-hover border-b border-border-subtle">
              <span className="text-xs text-text-secondary">Fix Diff</span>
              <button onClick={copyFix} className="text-xs flex items-center gap-1 text-text-secondary hover:text-text-primary transition-colors">
                <Copy className="w-3 h-3" />
                {copied ? "Copied!" : "Copy fix"}
              </button>
            </div>
            <pre className="p-4 overflow-x-auto text-sm font-mono leading-relaxed">
              <code className="text-text-primary">{vuln.fix_diff}</code>
            </pre>
          </div>
        )}

        <div className="flex items-center gap-4 text-xs text-text-tertiary">
          <span>Found by: {vuln.source_agent || "AI Reviewer"}</span>
          <span>Scan: {vuln.scan_id.slice(0, 8)}</span>
          <span>{new Date(vuln.created_at).toLocaleString()}</span>
        </div>
      </main>
    </div>
  );
}
