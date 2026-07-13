"use client";

import Sidebar from "@/components/Sidebar";
import { api, getMe } from "@/lib/api";
import { Plus, Scan, ExternalLink, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

interface User {
  id: string; email: string; name: string | null;
  plan: string; plan_status: string; trial_ends_at: string | null;
}

interface Project {
  id: string; name: string; repo_url: string | null;
  repo_provider: string; github_owner: string | null;
  github_repo_name: string | null;
  project_type: string;
  vuln_counts: { critical: number; high: number; medium: number; low: number; info: number };
  last_scan_at: string | null; created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newUrl, setNewUrl] = useState("");

  const fetchProjects = useCallback(async () => {
    const res = await api("/v1/projects");
    if (res.ok) {
      const data = await res.json();
      setProjects(data.projects || []);
    }
  }, []);

  useEffect(() => {
    getMe().then((u) => {
      if (!u) { router.push("/login"); return; }
      setUser(u);
      fetchProjects().finally(() => setLoading(false));
    });
  }, [router, fetchProjects]);

  async function createProject(e: React.FormEvent) {
    e.preventDefault();
    const res = await api("/v1/projects", {
      method: "POST",
      body: JSON.stringify({ name: newName, repo_url: newUrl || null }),
    });
    if (res.ok) {
      setShowCreate(false);
      setNewName("");
      setNewUrl("");
      fetchProjects();
    }
  }

  async function deleteProject(id: string) {
    if (!confirm("Delete this project? All scan data will be lost.")) return;
    await api(`/v1/projects/${id}`, { method: "DELETE" });
    fetchProjects();
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-text-secondary text-sm">Loading...</div>
      </div>
    );
  }

  if (!user) return null;

  const isTrial = user.plan_status === "trial";

  return (
    <div className="flex">
      <Sidebar user={user} />
      <main className="flex-1 min-h-screen px-8 py-10 max-w-[1000px]">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight mb-1">Projects</h1>
            <p className="text-text-secondary text-sm">{projects.length} project{projects.length !== 1 ? "s" : ""}</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 bg-accent text-accent-text font-medium text-sm px-4 py-2.5 rounded-md hover:bg-accent-hover active:scale-[0.98] transition-all"
          >
            <Plus className="w-4 h-4" />
            New Project
          </button>
        </div>

        {showCreate && (
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-6 mb-8">
            <form onSubmit={createProject} className="space-y-4 max-w-md">
              <h3 className="font-semibold">Create Project</h3>
              <input
                type="text" value={newName} onChange={e => setNewName(e.target.value)}
                required placeholder="Project name"
                className="w-full bg-bg-base border border-border-subtle rounded-md px-4 py-2.5 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-border-default"
              />
              <input
                type="url" value={newUrl} onChange={e => setNewUrl(e.target.value)}
                placeholder="GitHub URL (optional) — https://github.com/user/repo"
                className="w-full bg-bg-base border border-border-subtle rounded-md px-4 py-2.5 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-border-default"
              />
              <div className="flex gap-3">
                <button type="submit" className="bg-accent text-accent-text font-medium text-sm px-4 py-2 rounded-md hover:bg-accent-hover transition-colors">
                  Create
                </button>
                <button type="button" onClick={() => setShowCreate(false)} className="text-sm text-text-secondary hover:text-text-primary transition-colors">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {projects.length === 0 ? (
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-12 flex flex-col items-center text-center">
            <div className="w-16 h-16 rounded-full bg-bg-hover flex items-center justify-center mb-6">
              <Scan className="w-8 h-8 text-text-tertiary" />
            </div>
            <h2 className="text-lg font-semibold mb-2">No projects yet</h2>
            <p className="text-text-secondary text-sm max-w-md">
              Create a project to start scanning. Connect a GitHub repo or scan a local directory from the CLI.
            </p>
          </div>
        ) : (
          <div className="grid gap-4">
            {projects.map((p) => (
              <div key={p.id} className="bg-bg-surface border border-border-subtle rounded-xl hover:border-border-default transition-colors">
                <div className="p-5 flex items-center justify-between">
                  <Link href={`/dashboard/${p.id}`} className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm truncate">{p.name}</span>
                      {p.github_repo_name && (
                        <span className="text-xs text-text-tertiary flex items-center gap-1">
                          <ExternalLink className="w-3 h-3" />
                          {p.github_owner}/{p.github_repo_name}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {p.vuln_counts.critical > 0 && (
                        <span className="text-xs bg-severity-critical/10 text-severity-critical px-1.5 py-0.5 rounded font-medium">
                          {p.vuln_counts.critical} critical
                        </span>
                      )}
                      {p.vuln_counts.high > 0 && (
                        <span className="text-xs bg-severity-high/10 text-severity-high px-1.5 py-0.5 rounded font-medium">
                          {p.vuln_counts.high} high
                        </span>
                      )}
                      {p.vuln_counts.medium > 0 && (
                        <span className="text-xs bg-severity-medium/10 text-severity-medium px-1.5 py-0.5 rounded font-medium">
                          {p.vuln_counts.medium} medium
                        </span>
                      )}
                      {(p.vuln_counts.critical + p.vuln_counts.high + p.vuln_counts.medium) === 0 && (
                        <span className="text-xs text-text-tertiary">No vulnerabilities</span>
                      )}
                    </div>
                  </Link>
                  <button
                    onClick={() => deleteProject(p.id)}
                    className="text-text-tertiary hover:text-severity-critical transition-colors ml-4"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
