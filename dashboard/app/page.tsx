import { Shield, ArrowRight, GitBranch, Brain, Scan, FileText } from "lucide-react";
import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg-base">
      <header className="border-b border-border-subtle">
        <div className="max-w-[1100px] mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-accent" />
            <span className="font-semibold tracking-tight">CIOTX</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm text-text-secondary hover:text-text-primary transition-colors">Sign in</Link>
            <Link href="/signup" className="text-sm bg-accent text-accent-text font-medium px-4 py-2 rounded-md hover:bg-accent-hover transition-colors">Get started</Link>
          </div>
        </div>
      </header>

      <main>
        <section className="max-w-[1100px] mx-auto px-6 py-24 text-center">
          <h1 className="text-4xl font-semibold tracking-tight mb-4 max-w-2xl mx-auto leading-tight">
            Find vulnerabilities before attackers do
          </h1>
          <p className="text-lg text-text-secondary max-w-lg mx-auto mb-8">
            AI agents that read every line of your code, trace data across files, and report only what they can prove.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/signup" className="inline-flex items-center gap-2 bg-accent text-accent-text font-medium px-5 py-2.5 rounded-md hover:bg-accent-hover transition-colors">
              Start free trial <ArrowRight className="w-4 h-4" />
            </Link>
            <Link href="/login" className="text-sm text-text-secondary hover:text-text-primary transition-colors">Sign in</Link>
          </div>
        </section>

        <section className="max-w-[1100px] mx-auto px-6 pb-24">
          <div className="grid grid-cols-4 gap-6">
            {[
              { icon: Brain, title: "AI-First", desc: "Reads every line of code, understands context, finds vulnerabilities through reasoning — not pattern matching." },
              { icon: GitBranch, title: "Cross-File", desc: "Traces data from frontend to backend. Finds bugs that span multiple files and services." },
              { icon: Scan, title: "Zero Noise", desc: "Only reports what it can prove. Every finding includes code evidence, data path, and fix." },
              { icon: FileText, title: "Fix Included", desc: "Every vulnerability comes with a suggested fix and diff. One click to copy." },
            ].map(({ icon: Icon, title, desc }) => (
              <div key={title} className="bg-bg-surface border border-border-subtle rounded-xl p-6">
                <div className="w-10 h-10 rounded-lg bg-bg-hover flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-accent" />
                </div>
                <h3 className="font-semibold text-sm mb-2">{title}</h3>
                <p className="text-xs text-text-secondary leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border-subtle">
        <div className="max-w-[1100px] mx-auto px-6 py-8 flex items-center justify-between text-xs text-text-tertiary">
          <span>&copy; 2026 CIOTX</span>
          <div className="flex gap-6">
            <a href="https://github.com/iam-orsu/CiotxAI" className="hover:text-text-secondary transition-colors">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
