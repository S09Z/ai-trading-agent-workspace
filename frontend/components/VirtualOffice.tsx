"use client";

import { useEffect, useRef } from "react";
import type { LogEntry } from "@/lib/types";
import { WS_URL } from "@/lib/api";

// Maps AlphaOps backend agent names → 3D office character IDs
const BACKEND_TO_3D: Record<string, string> = {
  market_watch:      "market",
  news_hunter:       "technical",
  sentiment_analyst: "sentiment",
  risk_monitor:      "risk",
  research_analyst:  "fundamentals",
  orchestrator:      "portfolio",
};

export default function VirtualOffice() {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/logs/ws`);

    ws.onmessage = (e) => {
      const log: LogEntry = JSON.parse(e.data);
      const agentId = BACKEND_TO_3D[log.agent_name];
      const win = iframeRef.current?.contentWindow;
      if (!agentId || !win) return;

      const state = log.level === "error" ? "thinking" : "working";
      win.postMessage({ type: "agent-state", id: agentId, state }, "*");

      setTimeout(() => {
        iframeRef.current?.contentWindow?.postMessage(
          { type: "agent-state", id: agentId, state: "idle" },
          "*"
        );
      }, 4000);
    };

    return () => ws.close();
  }, []);

  return (
    <iframe
      ref={iframeRef}
      src="/virtual-office/index.html"
      className="rounded-xl border border-slate-700 w-full"
      style={{ height: "70vh", minHeight: "520px" }}
      title="Virtual Office — AI Investment Desk"
    />
  );
}
