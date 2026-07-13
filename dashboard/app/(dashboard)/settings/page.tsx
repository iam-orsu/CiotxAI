"use client";

import Sidebar from "@/components/Sidebar";
import { api, getMe } from "@/lib/api";
import { ExternalLink } from "lucide-react";
import { useEffect, useState } from "react";

interface UserInfo { email: string; name: string | null; plan: string; plan_status: string; github_username?: string; avatar_url?: string | null; }

export default function SettingsPage() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [connectingGitHub, setConnectingGitHub] = useState(false);
  const [ghStatus, setGhStatus] = useState("");

  useEffect(() => {
    getMe().then((u) => {
      if (!u) { window.location.href = "/login"; return; }
      setUser(u);
      setLoading(false);
    });
  }, []);

  async function connectGitHub() {
    setConnectingGitHub(true);
    const res = await api("/v1/github/connect");
    if (res.ok) {
      const data = await res.json();
      window.open(data.url, "_blank");
      setGhStatus("Complete the authorization in the new tab, then refresh this page.");
    } else {
      const err = await res.json();
      setGhStatus(err.detail || "GitHub OAuth not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env");
    }
    setConnectingGitHub(false);
  }

  if (loading) return <div className="flex h-screen"><Sidebar user={null} /><div className="flex-1 flex items-center justify-center text-text-secondary text-sm">Loading...</div></div>;
  if (!user) return null;

  return (
    <div className="flex">
      <Sidebar user={user} />
      <main className="flex-1 min-h-screen px-8 py-10 max-w-[700px]">
        <h1 className="text-2xl font-semibold tracking-tight mb-8">Settings</h1>

        <section className="mb-10">
          <h2 className="text-sm font-medium text-text-secondary mb-4">Account</h2>
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-6 space-y-4">
            <div className="flex justify-between">
              <span className="text-sm text-text-secondary">Email</span>
              <span className="text-sm">{user.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-text-secondary">Name</span>
              <span className="text-sm">{user.name || "Not set"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-text-secondary">Plan</span>
              <span className="text-sm capitalize">{user.plan} · {user.plan_status}</span>
            </div>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-sm font-medium text-text-secondary mb-4">GitHub</h2>
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-6">
            <p className="text-sm text-text-secondary mb-4">
              Connect your GitHub account to scan private repositories and enable PR scanning.
            </p>
            <button
              onClick={connectGitHub}
              disabled={connectingGitHub}
              className="inline-flex items-center gap-2 bg-bg-hover text-text-primary text-sm px-4 py-2 rounded-md border border-border-subtle hover:border-border-default transition-colors disabled:opacity-50"
            >
              <ExternalLink className="w-4 h-4" />
              {connectingGitHub ? "Connecting..." : "Connect GitHub"}
            </button>
            {ghStatus && <p className="text-sm text-text-secondary mt-3">{ghStatus}</p>}
          </div>
        </section>

        <section>
          <h2 className="text-sm font-medium text-text-secondary mb-4">API</h2>
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-6">
            <p className="text-sm text-text-secondary mb-4">
              Use the CLI to authenticate and trigger scans. Run <code className="text-xs bg-bg-hover px-1.5 py-0.5 rounded font-mono">ciotx login</code> to get started.
            </p>
            <a href="https://github.com/iam-orsu/CiotxAI" target="_blank" rel="noopener noreferrer"
               className="text-sm text-accent hover:underline inline-flex items-center gap-1">
              View on GitHub <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </section>
      </main>
    </div>
  );
}
