import Link from "next/link";
import { getLogs } from "@/lib/api";
import VirtualOffice from "@/components/VirtualOffice";
import ActivityLog from "@/components/ActivityLog";

export const dynamic = "force-dynamic";

export default async function OfficePage() {
  const logs = await getLogs();

  return (
    <main className="min-h-screen text-white p-6">
      <div className="max-w-5xl mx-auto space-y-6">

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold font-mono tracking-tight">Virtual Office</h1>
            <p className="text-sm text-slate-400">Murff Alpha agents — live</p>
          </div>
          <Link
            href="/"
            className="text-sm text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 px-4 py-2 rounded-lg transition-colors"
          >
            ← Dashboard
          </Link>
        </div>

        <VirtualOffice />

        <section>
          <h2 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">
            Live Feed
          </h2>
          <ActivityLog initial={logs} />
        </section>

      </div>
    </main>
  );
}
