"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  CrosshairMode,
  LineSeries,
  HistogramSeries,
  AreaSeries,
  CandlestickSeries,
} from "lightweight-charts";
import type { LineStyleOptions, SeriesOptionsCommon, AreaStyleOptions } from "lightweight-charts";

const TEXT = "#8892c0";
const GRID = "#2d3478";
const UP = "#35ed7e";
const DOWN = "#f87171";

export interface TimeValue {
  time: string;
  value: number;
}

export interface TimeOHLCV {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

export type SeriesConfig =
  | {
      kind: "line";
      data: TimeValue[];
      color: string;
      lineWidth?: number;
      title?: string;
    }
  | {
      kind: "histogram";
      data: (TimeValue & { color?: string })[];
      color: string;
      title?: string;
    }
  | {
      kind: "area";
      data: TimeValue[];
      lineColor: string;
      topColor: string;
      bottomColor: string;
      title?: string;
    }
  | {
      kind: "candle";
      data: TimeOHLCV[];
    };

export interface ThresholdLine {
  value: number;
  color: string;
}

interface Props {
  series: SeriesConfig[];
  thresholds?: ThresholdLine[];
  height?: number;
  /** title shown above the chart */
  label?: string;
}

export default function SeriesChart({
  series,
  thresholds = [],
  height = 160,
  label,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || series.length === 0) return;

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { color: "transparent" },
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

    for (const cfg of series) {
      if (cfg.kind === "candle") {
        const s = chart.addSeries(CandlestickSeries, {
          upColor: UP,
          downColor: DOWN,
          borderUpColor: UP,
          borderDownColor: DOWN,
          wickUpColor: UP,
          wickDownColor: DOWN,
        });
        s.setData(cfg.data);
      } else if (cfg.kind === "line") {
        const opts: Partial<LineStyleOptions & SeriesOptionsCommon> = {
          color: cfg.color,
          lineWidth: (cfg.lineWidth ?? 2) as 1 | 2 | 3 | 4,
        };
        if (cfg.title) opts.title = cfg.title;
        const s = chart.addSeries(LineSeries, opts);
        s.setData(cfg.data);
      } else if (cfg.kind === "histogram") {
        const s = chart.addSeries(HistogramSeries, { color: cfg.color });
        s.setData(cfg.data.map((d) => ({ ...d, color: d.color ?? cfg.color })));
      } else if (cfg.kind === "area") {
        const opts: Partial<AreaStyleOptions & SeriesOptionsCommon> = {
          lineColor: cfg.lineColor,
          topColor: cfg.topColor,
          bottomColor: cfg.bottomColor,
        };
        if (cfg.title) opts.title = cfg.title;
        const s = chart.addSeries(AreaSeries, opts);
        s.setData(cfg.data);
      }
    }

    // Draw threshold lines on the first series
    if (thresholds.length > 0) {
      // lightweight-charts v5: threshold lines via createPriceLine on the first series
      // We access the first added series via chart.series() — not available in v5 base API.
      // Instead we add transparent line series at the threshold values.
      for (const th of thresholds) {
        const s = chart.addSeries(LineSeries, {
          color: th.color,
          lineWidth: 1,
          lineStyle: 2, // dashed
        } as Partial<LineStyleOptions & SeriesOptionsCommon>);
        // Use the time range of the first series to span the threshold
        const firstSeries = series[0];
        if (firstSeries && "data" in firstSeries && Array.isArray(firstSeries.data)) {
          const times = (firstSeries.data as TimeValue[]).map((d) => d.time);
          if (times.length > 0) {
            s.setData([
              { time: times[0], value: th.value },
              { time: times[times.length - 1], value: th.value },
            ]);
          }
        }
      }
    }

    chart.timeScale().fitContent();
    return () => { chart.remove(); };
  }, [series, thresholds]);

  return (
    <div style={{ width: "100%" }}>
      {label && (
        <p
          className="text-[10px] uppercase tracking-wider mb-1 px-1"
          style={{ color: TEXT }}
        >
          {label}
        </p>
      )}
      <div
        ref={containerRef}
        style={{ height, width: "100%", borderRadius: "8px", overflow: "hidden" }}
      />
    </div>
  );
}
