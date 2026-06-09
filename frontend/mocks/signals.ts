import type { SignalOut } from "@/lib/types";

const minsAgo = (m: number) => new Date(Date.now() - m * 60_000).toISOString();

export const MOCK_SIGNALS: SignalOut[] = [
  {
    id: 1,
    ticker: "NVDA",
    signal_type: "bullish",
    confidence: 0.92,
    source_agent: "ResearchAnalyst",
    rationale:
      "Strong AI inference demand cycle continues. Data center revenue +122% YoY. Blackwell ramp ahead of schedule. Institutional accumulation visible in options flow.",
    grade_short: "A",
    grade_mid: "A",
    grade_long: "S",
    created_at: minsAgo(62),
  },
  {
    id: 2,
    ticker: "TSLA",
    signal_type: "bearish",
    confidence: 0.78,
    source_agent: "SentimentAnalyst",
    rationale:
      "Margin compression from EV price war continues. Delivery miss vs estimates two quarters running. Competition from BYD accelerating in key markets.",
    grade_short: "C",
    grade_mid: "B",
    grade_long: "B",
    created_at: minsAgo(15),
  },
  {
    id: 3,
    ticker: "AAPL",
    signal_type: "watchlist",
    confidence: 0.61,
    source_agent: "SentimentAnalyst",
    rationale:
      "iPhone cycle appears stable. Apple Intelligence rollout gaining traction. Watch for services revenue acceleration in Q3 earnings.",
    grade_short: "B",
    grade_mid: "A",
    grade_long: "A",
    created_at: minsAgo(45),
  },
  {
    id: 4,
    ticker: "MSFT",
    signal_type: "bullish",
    confidence: 0.87,
    source_agent: "ResearchAnalyst",
    rationale:
      "Azure growth reaccelerating on Copilot enterprise adoption. OpenAI partnership deepens moat. Cloud margins expanding.",
    grade_short: "A",
    grade_mid: "S",
    grade_long: "S",
    created_at: minsAgo(90),
  },
  {
    id: 5,
    ticker: "OKLO",
    signal_type: "bullish",
    confidence: 0.83,
    source_agent: "DiscoveryAgent",
    rationale:
      "Nuclear micro-reactor approval momentum. DOE backing for advanced fission. AI data center power demand making SMR story increasingly credible.",
    grade_short: "B",
    grade_mid: "A",
    grade_long: "S",
    created_at: minsAgo(20),
  },
  {
    id: 6,
    ticker: "META",
    signal_type: "bullish",
    confidence: 0.74,
    source_agent: "SentimentAnalyst",
    rationale:
      "Ad revenue growth holding. Llama 4 open-source positioning strengthens developer ecosystem. Reality Labs losses stabilising.",
    grade_short: "A",
    grade_mid: "A",
    grade_long: "B",
    created_at: minsAgo(130),
  },
  {
    id: 7,
    ticker: "PLTR",
    signal_type: "bullish",
    confidence: 0.71,
    source_agent: "DiscoveryAgent",
    rationale:
      "AIP enterprise deals accelerating. US government contract pipeline expanding. Profitable for 5 consecutive quarters.",
    grade_short: "B",
    grade_mid: "A",
    grade_long: "A",
    created_at: minsAgo(340),
  },
  {
    id: 8,
    ticker: "AMZN",
    signal_type: "watchlist",
    confidence: 0.65,
    source_agent: "SentimentAnalyst",
    rationale:
      "AWS growth re-accelerating on AI workloads. Retail margin improvement story intact. Monitoring Bedrock adoption by enterprise customers.",
    grade_short: "B",
    grade_mid: "A",
    grade_long: "A",
    created_at: minsAgo(200),
  },
];
