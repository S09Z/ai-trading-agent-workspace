import type { SwarmPreset } from "@/lib/types";

export const MOCK_PRESETS: SwarmPreset[] = [
  {
    name: "Earnings Research Desk",
    description: "Fundamentals + sentiment + risk feeding a research thesis",
    filename: "earnings_desk",
    agents: [
      { id: "fundamental", type: "FinancialAnalyst", depends_on: [] },
      { id: "sentiment", type: "SentimentAnalyst", depends_on: [] },
      { id: "risk", type: "RiskMonitor", depends_on: ["fundamental", "sentiment"] },
      { id: "research", type: "ResearchAnalyst", depends_on: ["risk"] },
    ],
  },
  {
    name: "Quant Strategy Desk",
    description: "Market scan + factor scoring into a research synthesis",
    filename: "quant_desk",
    agents: [
      { id: "market", type: "MarketWatch", depends_on: [] },
      { id: "factors", type: "FinancialAnalyst", depends_on: ["market"] },
      { id: "research", type: "ResearchAnalyst", depends_on: ["factors"] },
    ],
  },
];
