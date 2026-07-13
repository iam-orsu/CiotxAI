"use client";

import Sidebar from "@/components/Sidebar";
import { api, getMe } from "@/lib/api";
import { Check } from "lucide-react";
import { useEffect, useState } from "react";

interface UserInfo { email: string; name: string | null; plan: string; plan_status: string; trial_ends_at: string | null; }
interface SubInfo { has_subscription: boolean; plan: string; billing_period: string; status: string; scans_used: number; scans_limit: number; current_period_end: string; }

const PLAN_FEATURES: Record<string, string[]> = {
  starter: ["20 scans/month", "Up to 50K LOC", "AI code review", "GitHub repo connect", "Secrets detection", "Dependency CVE check", "Basic PDF report", "Email support"],
  pro: ["Unlimited scans", "Up to 200K LOC", "AI + cross-file analysis", "GitHub PR scanning", "24/7 scheduled monitoring", "Detailed PDF audit report", "5 team members", "Priority support"],
};

export default function BillingPage() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [sub, setSub] = useState<SubInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    getMe().then(async (u) => {
      if (!u) { window.location.href = "/login"; return; }
      setUser(u);
      const [subRes] = await Promise.all([
        api("/v1/billing/subscription"),
      ]);
      if (subRes.ok) setSub(await subRes.json());
      setLoading(false);
    });
  }, []);

  async function subscribe(plan: string, period: string) {
    setSubscribing(`${plan}-${period}`);
    setMsg("");
    const res = await api("/v1/billing/subscribe", {
      method: "POST",
      body: JSON.stringify({ plan, billing_period: period }),
    });
    const data = await res.json();
    setSubscribing("");
    if (res.ok) {
      setMsg(`Subscribed to ${plan} (${period})!`);
      const sr = await api("/v1/billing/subscription");
      if (sr.ok) setSub(await sr.json());
      // Refresh user to get updated plan
      const ur = await getMe();
      if (ur) setUser(ur);
    } else {
      setMsg(data.detail || "Subscription failed.");
    }
  }

  async function cancelSub() {
    if (!confirm("Cancel your subscription? Access continues until the end of the billing period.")) return;
    const res = await api("/v1/billing/cancel", { method: "POST" });
    if (res.ok) {
      setMsg("Subscription cancelled.");
      const sr = await api("/v1/billing/subscription");
      if (sr.ok) setSub(await sr.json());
    }
  }

  if (loading) return <div className="flex h-screen"><Sidebar user={null} /><div className="flex-1 flex items-center justify-center text-text-secondary text-sm">Loading...</div></div>;
  if (!user) return null;

  const isTrial = user.plan_status === "trial";
  const isPro = user.plan === "pro";

  return (
    <div className="flex">
      <Sidebar user={user} />
      <main className="flex-1 min-h-screen px-8 py-10 max-w-[900px]">
        <h1 className="text-2xl font-semibold tracking-tight mb-2">Billing</h1>
        <p className="text-text-secondary text-sm mb-8">Manage your subscription and billing.</p>

        {msg && (
          <div className="bg-status-success/10 border border-status-success/30 text-status-success text-sm px-4 py-3 rounded-md mb-6">{msg}</div>
        )}

        {isTrial && (
          <div className="bg-status-warning/10 border border-status-warning/30 rounded-xl p-6 mb-8">
            <h3 className="font-semibold mb-1">Trial Active</h3>
            <p className="text-sm text-text-secondary">
              Your 7-day Pro trial ends on {user.trial_ends_at ? new Date(user.trial_ends_at).toLocaleDateString() : "soon"}. Subscribe to keep scanning.
            </p>
          </div>
        )}

        {sub?.has_subscription && (
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-semibold capitalize">{sub.plan} Plan</h3>
                <p className="text-sm text-text-secondary">{sub.billing_period} · Status: {sub.status}</p>
              </div>
              <button onClick={cancelSub} className="text-sm text-text-secondary hover:text-severity-critical transition-colors">Cancel</button>
            </div>
            {sub.scans_limit > 0 && (
              <div className="bg-bg-base rounded-lg p-4">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-text-secondary">Scans this month</span>
                  <span className="tabular-nums">{sub.scans_used} / {sub.scans_limit}</span>
                </div>
                <div className="h-1.5 bg-bg-hover rounded-full overflow-hidden">
                  <div className="h-full bg-accent rounded-full transition-all"
                    style={{ width: `${Math.min(100, (sub.scans_used / sub.scans_limit) * 100)}%` }} />
                </div>
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          {(["starter", "pro"] as const).map((plan) => {
            const isCurrentPlan = !isTrial && ((plan === "starter" && !isPro) || (plan === "pro" && isPro));
            return (
              <div key={plan} className={`bg-bg-surface border rounded-xl p-6 ${
                isCurrentPlan ? "border-accent/50" : "border-border-subtle"
              }`}>
                <h3 className="text-lg font-semibold capitalize mb-1">{plan}</h3>
                <div className="mb-4">
                  <span className="text-2xl font-semibold tabular-nums">
                    {plan === "starter" ? "₹399" : "₹1,499"}
                  </span>
                  <span className="text-text-secondary text-sm">/mo</span>
                </div>

                <ul className="space-y-2 mb-6">
                  {(PLAN_FEATURES[plan] || []).map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-text-secondary">
                      <Check className="w-4 h-4 text-status-success mt-0.5 flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>

                {isCurrentPlan ? (
                  <div className="text-sm text-center text-text-tertiary py-2">Current plan</div>
                ) : (
                  <div className="space-y-2">
                    <button
                      onClick={() => subscribe(plan, "monthly")}
                      disabled={subscribing !== ""}
                      className="w-full bg-accent text-accent-text font-medium text-sm py-2 rounded-md hover:bg-accent-hover transition-colors disabled:opacity-50"
                    >
                      {subscribing === `${plan}-monthly` ? "..." : `Subscribe Monthly`}
                    </button>
                    <button
                      onClick={() => subscribe(plan, "annual")}
                      disabled={subscribing !== ""}
                      className="w-full border border-border-subtle text-text-secondary text-sm py-2 rounded-md hover:border-border-default hover:text-text-primary transition-colors disabled:opacity-50"
                    >
                      {subscribing === `${plan}-annual` ? "..." : `Annual (save 17%)`}
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
