import { Space_Grotesk, Inter } from "next/font/google";
import StockTerminal from "@/components/stock/StockTerminal";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});
const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export default async function StockPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  return (
    <div
      className={`${spaceGrotesk.variable} ${inter.variable} min-h-screen`}
      style={{ background: "#0a0d3a", color: "#e2e8f0" }}
    >
      <StockTerminal key={ticker.toUpperCase()} ticker={ticker.toUpperCase()} />
    </div>
  );
}
