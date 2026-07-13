"use client";

import { api, getMe } from "@/lib/api";
import { ArrowLeft, ExternalLink, Scan, Shield } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface Project {
  id: string; name: string; repo_url: string | null;
  github_owner: string | null; github_repo_name: string | null;
  vuln_counts: { critical: number; high: number; medium: number; low: number; info: number };
  last_scan_at: string | null; created_at: string;
}

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe().then((u) => {
      if (!u) { router.push("/login"); return; }
      api(`/v1/projects/${projectId}`).then(async (res) => {
        if (!res.ok) { router.push("/dashboard"); return; }
        setProject(await res.json());
        setLoading(false);
      });
    });
  }, [projectId, router]);

  if (loading || !project) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-text-secondary text-sm">Loading...</div>
      </div>
    );
  }

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
          <button className="flex items-center gap-2 bg-accent text-accent-text font-medium text-sm px-4 py-2.5 rounded-md hover:bg-accent-hover active:scale-[0.98] transition-all">
            <Scan className="w-4 h-4" />
            Scan Now
          </button>
        </div>

        <div className="grid grid-cols-5 gap-4 mb-8">
          {[
            { label: "Critical", count: project.vuln_counts.critical, color: "bg-severity-critical/10 text-severity-critical border-severity-critical/30" },
            { label: "High", count: project.vuln_counts.high, color: "bg-severity-high/10 text-severity-high border-severity-high/30" },
            { label: "Medium", count: project.vuln_counts.medium, color: "bg-severity-medium/10 text-severity-medium border-severity-medium/30" },
            { label: "Low", count: project.vuln_counts.low, color: "bg-severity-low/10 text-severity-low border-severity-low/30" },
            { label: "Info", count: project.vuln_counts.info, color: "bg-severity-info/10 text-severity-info border-severity-info/30" },
          ].map(({ label, count, color }) => (
            <div key={label} className={`border rounded-xl p-4 text-center ${color}`}>
              <div className="text-3xl font-semibold tabular-nums">{count}</div>
              <div className="text-xs mt-1 opacity-80">{label}</div>
            </div>
          ))}
        </div>

        <div className="bg-bg-surface border border-border-subtle rounded-xl p-12 flex flex-col items-center text-center">
          <div className="w-16 h-16 rounded-full bg-bg-hover flex items-center justify-center mb-6">
            <Scan className="w-8 h-8 text-text-tertiary" />
          </div>
          <h2 className="text-lg font-semibold mb-2">No scans yet</h2>
          <p className="text-text-secondary text-sm max-w-md">
            Run your first scan to find vulnerabilities in this project.
          </p>
        </div>
      </main>
    </div>
  );
}
