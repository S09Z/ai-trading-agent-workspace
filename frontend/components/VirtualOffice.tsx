"use client";

import { useEffect, useRef } from "react";
import type { LogEntry } from "@/lib/types";
import { WS_URL } from "@/lib/api";

const AGENTS = [
  "orchestrator",
  "news_hunter",
  "market_watch",
  "sentiment_analyst",
  "research_analyst",
  "risk_monitor",
] as const;

type AgentName = (typeof AGENTS)[number];
type SpriteState = "idle" | "active" | "sleeping" | "error";

// RGB tuples for each agent
const AGENT_COLOR: Record<AgentName, [number, number, number]> = {
  orchestrator:     [168,  85, 247],
  news_hunter:      [ 59, 130, 246],
  market_watch:     [ 34, 197,  94],
  sentiment_analyst:[249, 115,  22],
  research_analyst: [  6, 182, 212],
  risk_monitor:     [239,  68,  68],
};

// 2-row × 3-col grid of workstation centres [cx, cy]
const POSITIONS: [number, number][] = [
  [120, 150], [380, 150], [640, 150],
  [120, 300], [380, 300], [640, 300],
];

const W = 760;
const H = 380;
const S = 3; // pixel-art scale (each "pixel" = 3 canvas px)

function rgb([r, g, b]: [number, number, number], a = 1) {
  return `rgba(${r},${g},${b},${a})`;
}

function drawSprite(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  color: [number, number, number],
  state: SpriteState,
  frame: number
) {
  const bounce = state === "active" ? Math.round(Math.sin(frame * 0.25) * 2) : 0;
  const blink  = state === "error" && Math.floor(frame / 8) % 2 === 0;
  const dim    = state === "sleeping";
  const sy     = y + bounce;

  const bodyRgb = blink ? "#ef4444" : rgb(color, dim ? 0.4 : 1);
  const skinRgb = dim ? "#7a5040" : "#fcd5b4";

  // Head 4×4
  ctx.fillStyle = skinRgb;
  ctx.fillRect(x + S, sy, 4 * S, 4 * S);

  // Eyes
  if (dim) {
    ctx.fillStyle = "#5a3a28";
    ctx.fillRect(x + 2 * S, sy + 2 * S, 2 * S, 1);
    ctx.fillRect(x + 4 * S, sy + 2 * S, 2 * S, 1);
  } else {
    ctx.fillStyle = state === "active" ? "#ffffff" : "#1e293b";
    ctx.fillRect(x + 2 * S, sy + S, S, S);
    ctx.fillRect(x + 4 * S, sy + S, S, S);
  }

  // Body 6×4
  ctx.fillStyle = bodyRgb;
  ctx.fillRect(x, sy + 4 * S, 6 * S, 4 * S);

  // Arms — raised when active
  if (state === "active") {
    ctx.fillRect(x - S, sy + 2 * S, S, 3 * S);
    ctx.fillRect(x + 6 * S, sy + 2 * S, S, 3 * S);
  } else {
    ctx.fillRect(x - S, sy + 4 * S, S, 3 * S);
    ctx.fillRect(x + 6 * S, sy + 4 * S, S, 3 * S);
  }

  // Legs 2×3 each
  ctx.fillStyle = "#334155";
  ctx.fillRect(x + S,     sy + 8 * S, 2 * S, 3 * S);
  ctx.fillRect(x + 3 * S, sy + 8 * S, 2 * S, 3 * S);

  // Floating Z for sleeping
  if (dim) {
    const zOff = Math.floor(frame / 20) % 3;
    ctx.fillStyle = `rgba(148,163,184,${0.5 + zOff * 0.15})`;
    ctx.font = `${7 + zOff}px monospace`;
    ctx.textAlign = "left";
    ctx.fillText("z", x + 7 * S, sy - 2 - zOff * 3);
  }
}

function drawWorkstation(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  name: string,
  color: [number, number, number],
  state: SpriteState,
  frame: number
) {
  const isActive = state === "active";

  // Desk surface
  ctx.fillStyle = "#4a3728";
  ctx.fillRect(cx - 36, cy + 40, 88, 6);
  ctx.fillStyle = "#3d2b1f";
  ctx.fillRect(cx - 36, cy + 46, 88, 10);

  // Monitor stand
  ctx.fillStyle = "#374151";
  ctx.fillRect(cx + 4, cy + 28, 6, 14);

  // Monitor casing
  ctx.fillStyle = "#1e293b";
  ctx.fillRect(cx - 20, cy + 6, 48, 26);

  // Monitor screen
  ctx.fillStyle = isActive ? rgb(color, 0.25) : "#0f172a";
  ctx.fillRect(cx - 18, cy + 8, 44, 22);

  // Screen glow lines when active
  if (isActive) {
    for (let i = 0; i < 4; i++) {
      const alpha = 0.5 + Math.sin(frame * 0.12 + i * 1.2) * 0.3;
      ctx.fillStyle = rgb(color, alpha);
      ctx.fillRect(cx - 15, cy + 11 + i * 4, 16 + (i % 3) * 10, 2);
    }
  }

  // Sprite: offset so feet rest on desk level
  drawSprite(ctx, cx - 9, cy - 6, color, state, frame);

  // Name label
  const labelColor =
    state === "error" ? "#ef4444" : isActive ? rgb(color) : "#475569";
  ctx.fillStyle = labelColor;
  ctx.font = "9px monospace";
  ctx.textAlign = "center";
  ctx.fillText(name.replace(/_/g, " "), cx + 4, cy + 64);
}

export default function VirtualOffice() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // Keep agent states in a ref so the draw loop sees live values without re-render
  const stateRef = useRef<Record<string, SpriteState>>(
    Object.fromEntries(AGENTS.map((a) => [a, "sleeping"]))
  );
  const rafRef = useRef<number>(0);

  // WebSocket — flip sprite state on new log events
  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/logs/ws`);
    ws.onmessage = (e) => {
      const log: LogEntry = JSON.parse(e.data);
      if (!(AGENTS as readonly string[]).includes(log.agent_name)) return;
      const next: SpriteState = log.level === "error" ? "error" : "active";
      stateRef.current[log.agent_name] = next;
      setTimeout(() => {
        stateRef.current[log.agent_name] = "idle";
      }, 3000);
    };
    return () => ws.close();
  }, []);

  // Canvas draw loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let frame = 0;

    const draw = () => {
      frame++;

      // Background — dark office
      ctx.fillStyle = "#0f172a";
      ctx.fillRect(0, 0, W, H);

      // Back wall
      ctx.fillStyle = "#1a2744";
      ctx.fillRect(0, 0, W, H - 80);

      // Subtle grid on wall
      ctx.strokeStyle = "rgba(30,58,138,0.3)";
      ctx.lineWidth = 0.5;
      for (let gx = 0; gx <= W; gx += 80) {
        ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, H - 80); ctx.stroke();
      }
      for (let gy = 0; gy <= H - 80; gy += 60) {
        ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(W, gy); ctx.stroke();
      }

      // Floor
      ctx.fillStyle = "#0d1b2e";
      ctx.fillRect(0, H - 80, W, 80);
      ctx.strokeStyle = "#1e3a5f";
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(0, H - 80); ctx.lineTo(W, H - 80); ctx.stroke();

      // Header tag
      ctx.fillStyle = "#334155";
      ctx.font = "bold 10px monospace";
      ctx.textAlign = "left";
      ctx.fillText("// MURFF ALPHA — VIRTUAL OFFICE", 14, 18);

      // Draw each workstation
      AGENTS.forEach((agent, i) => {
        const [cx, cy] = POSITIONS[i];
        drawWorkstation(
          ctx, cx, cy,
          agent,
          AGENT_COLOR[agent],
          stateRef.current[agent] ?? "idle",
          frame
        );
      });

      rafRef.current = requestAnimationFrame(draw);
    };

    rafRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      width={W}
      height={H}
      className="rounded-lg border border-slate-700 w-full"
      style={{ imageRendering: "pixelated" }}
    />
  );
}
