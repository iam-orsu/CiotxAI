"use client";

import { logout } from "@/lib/api";
import { CreditCard, Folder, LogOut, Settings, Shield } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface Props {
  user: { email: string; plan: string; plan_status: string } | null;
}

export default function Sidebar({ user }: Props) {
  const pathname = usePathname();

  const links = [
    { href: "/dashboard", label: "Projects", icon: Folder },
    { href: "/billing", label: "Billing", icon: CreditCard },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/");

  return (
    <aside className="w-[220px] min-h-screen border-r border-border-subtle bg-bg-surface flex flex-col">
      <div className="px-4 py-4 border-b border-border-subtle">
        <Link href="/dashboard" className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-accent" />
          <span className="font-semibold tracking-tight text-sm">CIOTX</span>
        </Link>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
              isActive(href)
                ? "bg-bg-active text-text-primary font-medium"
                : "text-text-secondary hover:text-text-primary hover:bg-bg-hover"
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </Link>
        ))}
      </nav>

      {user && (
        <div className="px-3 py-4 border-t border-border-subtle space-y-2">
          <div className="px-3">
            <p className="text-xs text-text-secondary truncate">{user.email}</p>
            <span className={`text-xs font-medium ${
              user.plan_status === "trial" ? "text-status-warning" : "text-status-success"
            }`}>
              {user.plan_status === "trial" ? "Trial" : user.plan}
            </span>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-text-secondary hover:text-text-primary hover:bg-bg-hover w-full transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}
