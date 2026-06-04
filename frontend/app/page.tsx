import Link from "next/link";
import { getAgents, getLogs, getSignals } from "@/lib/api";
import AgentStatusBadge from "@/components/AgentStatusBadge";
import SignalCard from "@/components/SignalCard";
import ActivityLog from "@/components/ActivityLog";

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  const [agents, signals, logs] = await Promise.all([
    getAgents(),
    getSignals(),
    getLogs(),
  ]);

  return (
    <main className="min-h-screen text-white p-6">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold font-mono tracking-tight">Murff Alpha</h1>
            <p className="text-sm text-slate-400">AI Trading Intelligence Platform</p>
          </div>
          <Link
            href="/office"
            className="text-sm text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 px-4 py-2 rounded-lg transition-colors"
          >
            Virtual Office →
          </Link>
        </div>

        {/* Agent status row */}
        <section>
          <h2 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">
            Agents
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
            {agents.map((agent) => (
              <AgentStatusBadge key={agent.name} agent={agent} />
            ))}
          </div>
        </section>

        {/* Signals + log */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <section className="lg:col-span-2">
            <h2 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">
              Signals — last 6h
            </h2>
            {signals.length === 0 ? (
              <div className="bg-slate-800/30 border border-dashed border-slate-700 rounded-lg p-10 text-center text-slate-500 text-sm">
                No signals yet.{" "}
                <code className="font-mono text-slate-400">make cycle</code> to generate.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {signals.map((s) => (
                  <SignalCard key={s.id} signal={s} />
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">
              Activity Log
            </h2>
            <ActivityLog initial={logs} />
          </section>
        </div>

      </div>
    </main>
  );
}
