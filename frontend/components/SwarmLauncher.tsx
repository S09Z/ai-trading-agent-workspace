"use client";

import { useState } from "react";
import type { SwarmPreset } from "@/lib/types";
import { runSwarm } from "@/lib/api";

type Status =
  | { kind: "idle" }
  | { kind: "running" }
  | { kind: "queued" }
  | { kind: "error"; detail: string };

export default function SwarmLauncher({ presets }: { presets: SwarmPreset[] }) {
  const [selected, setSelected] = useState(presets[0]?.filename ?? "");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  if (presets.length === 0) {
    return (
      <div className="bg-slate-800/30 border border-dashed border-slate-700 rounded-lg p-6 text-center text-slate-500 text-sm">
        No swarm presets found. Add a YAML file under{" "}
        <code className="font-mono text-slate-400">config/swarm_presets/</code>.
      </div>
    );
  }

  const current = presets.find((p) => p.filename === selected);

  async function launch() {
    setStatus({ kind: "running" });
    const res = await runSwarm(selected);
    setStatus(res.ok ? { kind: "queued" } : { kind: "error", detail: res.detail ?? "failed" });
  }

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-3">
        <select
          value={selected}
          onChange={(e) => {
            setSelected(e.target.value);
            setStatus({ kind: "idle" });
          }}
          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-white focus:outline-none focus:border-slate-500"
        >
          {presets.map((p) => (
            <option key={p.filename} value={p.filename}>
              {p.name} ({p.agents.length} agents)
            </option>
          ))}
        </select>
        <button
          onClick={launch}
          disabled={status.kind === "running"}
          className="text-sm font-mono px-4 py-2 rounded-lg border border-slate-600 text-white hover:border-slate-400 hover:bg-slate-700/50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {status.kind === "running" ? "Running…" : "Run"}
        </button>
      </div>

      {current?.description && (
        <p className="text-xs text-slate-400">{current.description}</p>
      )}

      {status.kind === "queued" && (
        <p className="text-xs font-mono text-green-400">
          queued ✓ — watch the Activity Log for progress
        </p>
      )}
      {status.kind === "error" && (
        <p className="text-xs font-mono text-red-400">error: {status.detail}</p>
      )}
    </div>
  );
}
