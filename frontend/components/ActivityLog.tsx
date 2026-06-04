"use client";

import { useEffect, useRef, useState } from "react";
import type { LogEntry } from "@/lib/types";
import { WS_URL } from "@/lib/api";

const LEVEL_COLOR: Record<string, string> = {
  info:    "text-blue-400",
  warning: "text-yellow-400",
  error:   "text-red-400",
};

function timeStr(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function ActivityLog({ initial }: { initial: LogEntry[] }) {
  const [entries, setEntries] = useState<LogEntry[]>(
    [...initial].reverse().slice(-50)
  );
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/logs/ws`);
    ws.onmessage = (e) => {
      const log: LogEntry = JSON.parse(e.data);
      setEntries((prev) => [...prev.slice(-49), log]);
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 h-64 overflow-y-auto p-3 font-mono text-xs space-y-1">
      {entries.length === 0 && (
        <p className="text-slate-600 text-center py-4">No activity yet.</p>
      )}
      {entries.map((e) => (
        <div key={e.id} className="flex gap-2 items-start leading-relaxed">
          <span className="text-slate-600 shrink-0">{timeStr(e.created_at)}</span>
          <span className="text-purple-400 shrink-0 truncate max-w-24">{e.agent_name}</span>
          <span className={`shrink-0 ${LEVEL_COLOR[e.level] ?? "text-slate-300"}`}>
            [{e.action}]
          </span>
          <span className="text-slate-300 break-all">{e.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
