"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  CrosshairMode,
  CandlestickSeries,
  HistogramSeries,
} from "lightweight-charts";
import type { StockBar } from "@/lib/types";
import { toVolumeBars } from "@/lib/indicators";

const CHART_BG = "transparent";
const TEXT = "#8892c0";
const GRID = "#2d3478";
const UP = "#35ed7e";
const DOWN = "#f87171";
const VOL_UP = "rgba(53,237,126,0.4)";
const VOL_DOWN = "rgba(248,113,113,0.4)";

interface Props {
  bars: StockBar[];
  height?: number;
}

export default function CandleVolumeChart({ bars, height = 340 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || bars.length === 0) return;

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { color: CHART_BG },
        textColor: TEXT,
      },
      grid: {
        vertLines: { color: GRID },
        horzLines: { color: GRID },
      },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: { borderColor: GRID },
      rightPriceScale: { borderColor: GRID },
    });

    // Candlestick series in pane 0
    const candles = chart.addSeries(CandlestickSeries, {
      upColor: UP,
      downColor: DOWN,
      borderUpColor: UP,
      borderDownColor: DOWN,
      wickUpColor: UP,
      wickDownColor: DOWN,
    });
    candles.setData(
      bars.map((b) => ({ time: b.t, open: b.o, high: b.h, low: b.l, close: b.c }))
    );

    // Volume histogram in pane 1
    const vol = chart.addSeries(
      HistogramSeries,
      {
        priceFormat: { type: "volume" },
        priceScaleId: "vol",
      },
      1
    );
    vol.priceScale().applyOptions({ scaleMargins: { top: 0.1, bottom: 0 } });
    vol.setData(toVolumeBars(bars, VOL_UP, VOL_DOWN));

    chart.timeScale().fitContent();

    return () => { chart.remove(); };
  }, [bars]);

  return (
    <div
      ref={containerRef}
      style={{ height, width: "100%", borderRadius: "12px", overflow: "hidden" }}
    />
  );
}
