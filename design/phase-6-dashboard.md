# Phase 6 — React Dashboard

## Goal

Build a professional-looking React dashboard that displays trading bot data: positions, trade history with AI reasoning, performance analytics, and model insights. Styled as a dark trading terminal.

## Depends On

- Phase 4: Data files exist in `data/` (trades.json, daily_summaries.json, latest_decisions.json)
- Phase 1: `state.json` exists at repo root

## What the Next Phase Expects

- `dashboard/` directory contains a complete Vite + React + TypeScript app
- `npm run dev` works and shows the dashboard locally
- `npm run build` produces a production build in `dashboard/dist/`
- The dashboard fetches data at runtime from `raw.githubusercontent.com`

## Project Scaffold

### 1. Initialize the project

```bash
cd dashboard
npm create vite@latest . -- --template react-ts
npm install react-router-dom recharts lightweight-charts lucide-react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 2. `dashboard/package.json`

After initialization, ensure these dependencies are present:

```json
{
    "name": "trading-bot-dashboard",
    "private": true,
    "type": "module",
    "scripts": {
        "dev": "vite",
        "build": "tsc && vite build",
        "preview": "vite preview"
    },
    "dependencies": {
        "react": "^18.3.0",
        "react-dom": "^18.3.0",
        "react-router-dom": "^6.26.0",
        "recharts": "^2.12.0",
        "lightweight-charts": "^4.2.0",
        "lucide-react": "^0.400.0"
    },
    "devDependencies": {
        "@types/react": "^18.3.0",
        "@types/react-dom": "^18.3.0",
        "@vitejs/plugin-react": "^4.3.0",
        "autoprefixer": "^10.4.0",
        "postcss": "^8.4.0",
        "tailwindcss": "^3.4.0",
        "typescript": "^5.5.0",
        "vite": "^5.4.0"
    }
}
```

### 3. `dashboard/vite.config.ts`

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],
    base: "/trading-bot/",
});
```

IMPORTANT: `base` must match your GitHub repository name. If your repo is named `my-trading-bot`, set `base: "/my-trading-bot/"`.

### 4. `dashboard/tailwind.config.js`

```javascript
/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    theme: {
        extend: {},
    },
    plugins: [],
};
```

### 5. `dashboard/postcss.config.js`

```javascript
export default {
    plugins: {
        tailwindcss: {},
        autoprefixer: {},
    },
};
```

### 6. `dashboard/tsconfig.json`

```json
{
    "compilerOptions": {
        "target": "ES2020",
        "useDefineForClassFields": true,
        "lib": ["ES2020", "DOM", "DOM.Iterable"],
        "module": "ESNext",
        "skipLibCheck": true,
        "moduleResolution": "bundler",
        "allowImportingTsExtensions": true,
        "isolatedModules": true,
        "moduleDetection": "force",
        "noEmit": true,
        "jsx": "react-jsx",
        "strict": true,
        "noUnusedLocals": true,
        "noUnusedParameters": true,
        "noFallthroughCasesInSwitch": true
    },
    "include": ["src"]
}
```

---

## Source Files

### 7. `dashboard/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Trading Bot Dashboard</title>
</head>
<body class="bg-gray-950 text-gray-100">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

### 8. `dashboard/src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 9. `dashboard/src/main.tsx`

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
        <BrowserRouter basename="/trading-bot/">
            <App />
        </BrowserRouter>
    </React.StrictMode>
);
```

IMPORTANT: `basename` in BrowserRouter must match the `base` in vite.config.ts.

### 10. `dashboard/src/App.tsx`

```tsx
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import PositionsPage from "./pages/PositionsPage";
import TradeHistoryPage from "./pages/TradeHistoryPage";
import PerformancePage from "./pages/PerformancePage";
import ModelInsightsPage from "./pages/ModelInsightsPage";

function App() {
    return (
        <Layout>
            <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/positions" element={<PositionsPage />} />
                <Route path="/trades" element={<TradeHistoryPage />} />
                <Route path="/performance" element={<PerformancePage />} />
                <Route path="/insights" element={<ModelInsightsPage />} />
            </Routes>
        </Layout>
    );
}

export default App;
```

---

## Type Definitions

### 11. `dashboard/src/types/index.ts`

```typescript
export interface Position {
    ticker: string;
    quantity: number;
    entry_price: number;
    entry_time: string;
    stop_loss: number;
    take_profit: number;
}

export interface Trade {
    id: string;
    ticker: string;
    yf_symbol: string;
    action: "BUY" | "SELL";
    quantity: number;
    price: number;
    value: number;
    time: string;
    reasoning: string;
    confidence: number | null;
    indicators: IndicatorSnapshot | null;
    stop_loss: number | null;
    take_profit: number | null;
    pnl: number | null;
}

export interface IndicatorSnapshot {
    rsi_14: number;
    macd: number;
    macd_signal: number;
    macd_histogram: number;
    bb_pct: number;
    ema_trend: "bullish" | "bearish";
}

export interface FullIndicators {
    current_price: number;
    rsi_14: number;
    macd: number;
    macd_signal: number;
    macd_histogram: number;
    bb_upper: number;
    bb_middle: number;
    bb_lower: number;
    bb_pct: number;
    ema_9: number;
    ema_21: number;
    ema_trend: "bullish" | "bearish";
    volume: number;
    price_change_pct: number;
}

export interface DailySummary {
    date: string;
    pnl: number;
    cumulative_pnl: number;
    trades_count: number;
    buys: number;
    sells: number;
    wins: number;
    losses: number;
    win_rate: number;
    best_trade_pnl: number;
    worst_trade_pnl: number;
    positions_open: number;
}

export interface Decision {
    ticker: string;
    yf_symbol: string;
    action: "BUY" | "SELL" | "HOLD";
    confidence: number;
    reasoning: string;
    was_executed: boolean;
    rejection_reason: string | null;
    indicators: FullIndicators | null;
}

export interface LatestDecisions {
    run_time: string | null;
    decisions: Decision[];
}

export interface BotState {
    positions: Position[];
    daily_pnl: number;
    trading_day: string | null;
    trade_history: unknown[];
    last_run: string | null;
}
```

---

## Data Fetching

### 12. `dashboard/src/lib/config.ts`

```typescript
const GITHUB_OWNER = "YOUR_GITHUB_USERNAME";
const GITHUB_REPO = "trading-bot";
const BRANCH = "main";

const BASE_URL = `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/${BRANCH}`;

export const DATA_URLS = {
    state: `${BASE_URL}/state.json`,
    trades: `${BASE_URL}/data/trades.json`,
    dailySummaries: `${BASE_URL}/data/daily_summaries.json`,
    latestDecisions: `${BASE_URL}/data/latest_decisions.json`,
} as const;
```

IMPORTANT: Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username. The repository must be public for `raw.githubusercontent.com` to work without authentication.

### 13. `dashboard/src/hooks/useData.ts`

```typescript
import { useState, useEffect, useCallback } from "react";
import { DATA_URLS } from "../lib/config";

type DataKey = keyof typeof DATA_URLS;

interface UseDataResult<T> {
    data: T;
    loading: boolean;
    error: string | null;
    refetch: () => void;
}

export function useData<T>(key: DataKey, fallback: T): UseDataResult<T> {
    const [data, setData] = useState<T>(fallback);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const url = `${DATA_URLS[key]}?t=${Date.now()}`;
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const json = await response.json();
            setData(json);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unknown error");
            setData(fallback);
        } finally {
            setLoading(false);
        }
    }, [key]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    return { data, loading, error, refetch: fetchData };
}
```

The `?t=${Date.now()}` query parameter busts GitHub's CDN cache to ensure fresh data.

### 13b. Standard Loading and Error States

Every page should use these patterns consistently (added per product review):

**Loading state** — show a pulsing skeleton placeholder:

```tsx
function LoadingSkeleton() {
    return (
        <div className="animate-pulse space-y-4">
            <div className="h-8 bg-gray-800 rounded w-1/4" />
            <div className="grid grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-24 bg-gray-800 rounded-xl" />
                ))}
            </div>
            <div className="h-64 bg-gray-800 rounded-xl" />
        </div>
    );
}
```

**Error state** — show a clear error with retry button:

```tsx
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
    return (
        <div className="bg-red-900/20 border border-red-800 rounded-xl p-6 text-center">
            <p className="text-red-400 mb-3">Failed to load data: {message}</p>
            <button
                onClick={onRetry}
                className="px-4 py-2 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 text-sm"
            >
                Retry
            </button>
        </div>
    );
}
```

**Usage pattern in every page:**

```tsx
const { data, loading, error, refetch } = useData<SomeType>("key", fallback);

if (loading) return <LoadingSkeleton />;
if (error) return <ErrorState message={error} onRetry={refetch} />;
// ... render data
```

Place `LoadingSkeleton` and `ErrorState` in `dashboard/src/components/StatusStates.tsx` and import them in every page.

---

## Layout Component

### 14. `dashboard/src/components/Layout.tsx`

Sidebar navigation with dark theme. Contains links to all 5 pages.

```tsx
import { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import {
    LayoutDashboard,
    Briefcase,
    History,
    TrendingUp,
    Brain,
} from "lucide-react";

const navItems = [
    { to: "/", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/positions", icon: Briefcase, label: "Positions" },
    { to: "/trades", icon: History, label: "Trade History" },
    { to: "/performance", icon: TrendingUp, label: "Performance" },
    { to: "/insights", icon: Brain, label: "Model Insights" },
];

interface LayoutProps {
    children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
    return (
        <div className="flex h-screen">
            {/* Sidebar */}
            <nav className="w-60 bg-gray-900 border-r border-gray-800 flex flex-col p-4">
                <h1 className="text-lg font-bold text-white mb-2 px-3">
                    Trading Bot
                </h1>
                {/* DEMO banner — remove or change when switching to live */}
                <div className="mx-3 mb-6 px-2 py-1 bg-yellow-900/50 border border-yellow-700 rounded text-xs text-yellow-300 text-center font-medium">
                    DEMO ACCOUNT
                </div>
                <ul className="space-y-1">
                    {navItems.map(({ to, icon: Icon, label }) => (
                        <li key={to}>
                            <NavLink
                                to={to}
                                end={to === "/"}
                                className={({ isActive }) =>
                                    `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                                        isActive
                                            ? "bg-gray-800 text-white"
                                            : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                                    }`
                                }
                            >
                                <Icon size={18} />
                                {label}
                            </NavLink>
                        </li>
                    ))}
                </ul>
            </nav>

            {/* Main content */}
            <main className="flex-1 overflow-y-auto bg-gray-950 p-8">
                {children}
            </main>
        </div>
    );
}
```

---

## Reusable Components

### 15. `dashboard/src/components/SummaryCards.tsx`

Four cards in a row: Total P&L, Today's P&L, Win Rate, Open Positions.

```tsx
import { DailySummary, BotState } from "../types";

interface SummaryCardsProps {
    summaries: DailySummary[];
    state: BotState;
}

export default function SummaryCards({ summaries, state }: SummaryCardsProps) {
    const latestSummary = summaries[summaries.length - 1];
    const cumulativePnl = latestSummary?.cumulative_pnl ?? 0;
    const todayPnl = state.daily_pnl;
    const totalTrades = summaries.reduce((sum, s) => sum + s.trades_count, 0);
    const totalWins = summaries.reduce((sum, s) => sum + s.wins, 0);
    const totalLosses = summaries.reduce((sum, s) => sum + s.losses, 0);
    const winRate =
        totalWins + totalLosses > 0
            ? ((totalWins / (totalWins + totalLosses)) * 100).toFixed(1)
            : "0.0";

    const cards = [
        {
            label: "Total P&L",
            value: `$${cumulativePnl.toFixed(2)}`,
            color: cumulativePnl >= 0 ? "text-emerald-400" : "text-red-400",
        },
        {
            label: "Today's P&L",
            value: `$${todayPnl.toFixed(2)}`,
            color: todayPnl >= 0 ? "text-emerald-400" : "text-red-400",
        },
        {
            label: "Win Rate",
            value: `${winRate}%`,
            color: "text-blue-400",
        },
        {
            label: "Open Positions",
            value: `${state.positions.length}`,
            color: "text-blue-400",
        },
    ];

    return (
        <div className="grid grid-cols-4 gap-4">
            {cards.map((card) => (
                <div
                    key={card.label}
                    className="bg-gray-900 rounded-xl border border-gray-800 p-6"
                >
                    <p className="text-sm text-gray-400 mb-1">{card.label}</p>
                    <p className={`text-2xl font-bold ${card.color}`}>
                        {card.value}
                    </p>
                </div>
            ))}
        </div>
    );
}
```

### 16. `dashboard/src/components/PnLChart.tsx`

Cumulative P&L line chart using Recharts.

```tsx
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";
import { DailySummary } from "../types";

interface PnLChartProps {
    summaries: DailySummary[];
}

export default function PnLChart({ summaries }: PnLChartProps) {
    if (summaries.length === 0) {
        return (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
                <h3 className="text-sm font-medium text-gray-400 mb-4">
                    Cumulative P&L
                </h3>
                <p className="text-gray-500 text-center py-12">
                    No data yet — trades will appear here
                </p>
            </div>
        );
    }

    return (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
            <h3 className="text-sm font-medium text-gray-400 mb-4">
                Cumulative P&L
            </h3>
            <ResponsiveContainer width="100%" height={300}>
                <LineChart data={summaries}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} />
                    <YAxis stroke="#9CA3AF" fontSize={12} />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: "#1F2937",
                            border: "1px solid #374151",
                            borderRadius: "8px",
                            color: "#F3F4F6",
                        }}
                    />
                    <Line
                        type="monotone"
                        dataKey="cumulative_pnl"
                        stroke="#34D399"
                        strokeWidth={2}
                        dot={false}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
```

### 17. `dashboard/src/components/TradeTable.tsx`

Table of trades with expandable rows showing AI reasoning.

```tsx
import { useState } from "react";
import { Trade } from "../types";
import { ChevronDown, ChevronRight } from "lucide-react";

interface TradeTableProps {
    trades: Trade[];
    limit?: number;
}

export default function TradeTable({ trades, limit }: TradeTableProps) {
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const displayed = limit ? trades.slice(-limit).reverse() : [...trades].reverse();

    if (displayed.length === 0) {
        return (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
                <p className="text-gray-500 text-center py-8">No trades yet</p>
            </div>
        );
    }

    return (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-gray-800">
                        <th className="text-left p-4 text-gray-400 font-medium"></th>
                        <th className="text-left p-4 text-gray-400 font-medium">Time</th>
                        <th className="text-left p-4 text-gray-400 font-medium">Ticker</th>
                        <th className="text-left p-4 text-gray-400 font-medium">Action</th>
                        <th className="text-right p-4 text-gray-400 font-medium">Qty</th>
                        <th className="text-right p-4 text-gray-400 font-medium">Price</th>
                        <th className="text-right p-4 text-gray-400 font-medium">P&L</th>
                        <th className="text-right p-4 text-gray-400 font-medium">Confidence</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                    {displayed.map((trade) => (
                        <>
                            <tr
                                key={trade.id}
                                className="hover:bg-gray-800 cursor-pointer"
                                onClick={() =>
                                    setExpandedId(
                                        expandedId === trade.id ? null : trade.id
                                    )
                                }
                            >
                                <td className="p-4 text-gray-500">
                                    {expandedId === trade.id ? (
                                        <ChevronDown size={14} />
                                    ) : (
                                        <ChevronRight size={14} />
                                    )}
                                </td>
                                <td className="p-4 text-gray-300">
                                    {new Date(trade.time).toLocaleString()}
                                </td>
                                <td className="p-4 text-white font-medium">
                                    {trade.yf_symbol}
                                </td>
                                <td className="p-4">
                                    <span
                                        className={`px-2 py-1 rounded text-xs font-medium ${
                                            trade.action === "BUY"
                                                ? "bg-emerald-900 text-emerald-300"
                                                : "bg-red-900 text-red-300"
                                        }`}
                                    >
                                        {trade.action}
                                    </span>
                                </td>
                                <td className="p-4 text-right text-gray-300">
                                    {trade.quantity}
                                </td>
                                <td className="p-4 text-right text-gray-300">
                                    ${trade.price.toFixed(2)}
                                </td>
                                <td
                                    className={`p-4 text-right font-medium ${
                                        trade.pnl === null
                                            ? "text-gray-500"
                                            : trade.pnl >= 0
                                            ? "text-emerald-400"
                                            : "text-red-400"
                                    }`}
                                >
                                    {trade.pnl !== null
                                        ? `$${trade.pnl.toFixed(2)}`
                                        : "—"}
                                </td>
                                <td className="p-4 text-right text-gray-300">
                                    {trade.confidence !== null
                                        ? `${(trade.confidence * 100).toFixed(0)}%`
                                        : "—"}
                                </td>
                            </tr>
                            {expandedId === trade.id && (
                                <tr key={`${trade.id}-detail`}>
                                    <td
                                        colSpan={8}
                                        className="p-4 bg-gray-800/50"
                                    >
                                        <p className="text-sm text-gray-300 mb-2">
                                            <span className="text-gray-500">
                                                AI Reasoning:{" "}
                                            </span>
                                            {trade.reasoning}
                                        </p>
                                        {trade.indicators && (
                                            <div className="flex gap-4 text-xs text-gray-400">
                                                <span>
                                                    RSI: {trade.indicators.rsi_14}
                                                </span>
                                                <span>
                                                    MACD: {trade.indicators.macd}
                                                </span>
                                                <span>
                                                    BB%: {trade.indicators.bb_pct}
                                                </span>
                                                <span>
                                                    Trend: {trade.indicators.ema_trend}
                                                </span>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            )}
                        </>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
```

### 18. `dashboard/src/components/PositionCard.tsx`

Card displaying a single open position.

```tsx
import { Position } from "../types";

interface PositionCardProps {
    position: Position;
}

export default function PositionCard({ position }: PositionCardProps) {
    return (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
            <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-bold text-white">
                    {position.ticker.replace("_US_EQ", "")}
                </h3>
                <span className="text-xs text-gray-500">
                    {new Date(position.entry_time).toLocaleDateString()}
                </span>
            </div>
            <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                    <span className="text-gray-400">Quantity</span>
                    <span className="text-white">{position.quantity}</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-400">Entry Price</span>
                    <span className="text-white">
                        ${position.entry_price.toFixed(2)}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-400">Stop Loss</span>
                    <span className="text-red-400">
                        ${position.stop_loss.toFixed(2)}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-400">Take Profit</span>
                    <span className="text-emerald-400">
                        ${position.take_profit.toFixed(2)}
                    </span>
                </div>
            </div>
        </div>
    );
}
```

### 19. `dashboard/src/components/DecisionCard.tsx`

Card showing a single Gemini decision with indicator values and reasoning.

```tsx
import { Decision } from "../types";

interface DecisionCardProps {
    decision: Decision;
}

export default function DecisionCard({ decision }: DecisionCardProps) {
    const actionColors = {
        BUY: "bg-emerald-900 text-emerald-300",
        SELL: "bg-red-900 text-red-300",
        HOLD: "bg-gray-700 text-gray-300",
    };

    return (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
            <div className="flex justify-between items-start mb-4">
                <div>
                    <h3 className="text-lg font-bold text-white">
                        {decision.yf_symbol}
                    </h3>
                    <span className="text-xs text-gray-500">
                        {decision.ticker}
                    </span>
                </div>
                <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                        actionColors[decision.action]
                    }`}
                >
                    {decision.action}
                </span>
            </div>

            {/* Confidence bar */}
            <div className="mb-4">
                <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-400">Confidence</span>
                    <span className="text-gray-300">
                        {(decision.confidence * 100).toFixed(0)}%
                    </span>
                </div>
                <div className="w-full h-2 bg-gray-800 rounded-full">
                    <div
                        className="h-2 rounded-full bg-blue-500"
                        style={{ width: `${decision.confidence * 100}%` }}
                    />
                </div>
            </div>

            {/* Reasoning */}
            <p className="text-sm text-gray-300 mb-4">{decision.reasoning}</p>

            {/* Execution status */}
            <div className="mb-4">
                {decision.was_executed ? (
                    <span className="text-xs text-emerald-400">Executed</span>
                ) : (
                    <span className="text-xs text-gray-500">
                        Not executed: {decision.rejection_reason}
                    </span>
                )}
            </div>

            {/* Indicators grid */}
            {decision.indicators && (
                <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex justify-between">
                        <span className="text-gray-500">Price</span>
                        <span className="text-gray-300">
                            ${decision.indicators.current_price.toFixed(2)}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-500">RSI(14)</span>
                        <span className="text-gray-300">
                            {decision.indicators.rsi_14}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-500">MACD</span>
                        <span className="text-gray-300">
                            {decision.indicators.macd}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-500">BB %B</span>
                        <span className="text-gray-300">
                            {decision.indicators.bb_pct}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-500">EMA Trend</span>
                        <span
                            className={
                                decision.indicators.ema_trend === "bullish"
                                    ? "text-emerald-400"
                                    : "text-red-400"
                            }
                        >
                            {decision.indicators.ema_trend}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-500">Volume</span>
                        <span className="text-gray-300">
                            {(decision.indicators.volume / 1e6).toFixed(1)}M
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
}
```

### 20. `dashboard/src/components/PerformanceCharts.tsx`

Daily P&L bar chart and win/loss pie chart.

```tsx
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
} from "recharts";
import { DailySummary } from "../types";

interface PerformanceChartsProps {
    summaries: DailySummary[];
}

export default function PerformanceCharts({
    summaries,
}: PerformanceChartsProps) {
    const totalWins = summaries.reduce((s, d) => s + d.wins, 0);
    const totalLosses = summaries.reduce((s, d) => s + d.losses, 0);
    const pieData = [
        { name: "Wins", value: totalWins },
        { name: "Losses", value: totalLosses },
    ];
    const PIE_COLORS = ["#34D399", "#F87171"];

    return (
        <div className="grid grid-cols-2 gap-6">
            {/* Daily P&L Bar Chart */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
                <h3 className="text-sm font-medium text-gray-400 mb-4">
                    Daily P&L
                </h3>
                {summaries.length === 0 ? (
                    <p className="text-gray-500 text-center py-12">No data yet</p>
                ) : (
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={summaries}>
                            <CartesianGrid
                                strokeDasharray="3 3"
                                stroke="#374151"
                            />
                            <XAxis
                                dataKey="date"
                                stroke="#9CA3AF"
                                fontSize={12}
                            />
                            <YAxis stroke="#9CA3AF" fontSize={12} />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: "#1F2937",
                                    border: "1px solid #374151",
                                    borderRadius: "8px",
                                    color: "#F3F4F6",
                                }}
                            />
                            <Bar dataKey="pnl">
                                {summaries.map((entry, index) => (
                                    <Cell
                                        key={index}
                                        fill={
                                            entry.pnl >= 0
                                                ? "#34D399"
                                                : "#F87171"
                                        }
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                )}
            </div>

            {/* Win/Loss Pie Chart */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
                <h3 className="text-sm font-medium text-gray-400 mb-4">
                    Win / Loss Ratio
                </h3>
                {totalWins + totalLosses === 0 ? (
                    <p className="text-gray-500 text-center py-12">No data yet</p>
                ) : (
                    <ResponsiveContainer width="100%" height={250}>
                        <PieChart>
                            <Pie
                                data={pieData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={90}
                                paddingAngle={5}
                                dataKey="value"
                                label={({ name, value }) =>
                                    `${name}: ${value}`
                                }
                            >
                                {pieData.map((_, index) => (
                                    <Cell
                                        key={index}
                                        fill={PIE_COLORS[index]}
                                    />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: "#1F2937",
                                    border: "1px solid #374151",
                                    borderRadius: "8px",
                                    color: "#F3F4F6",
                                }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                )}
            </div>
        </div>
    );
}
```

---

## Page Components

### 21. `dashboard/src/pages/DashboardPage.tsx`

Overview page: summary cards, P&L chart, recent trades.

```tsx
import { useData } from "../hooks/useData";
import SummaryCards from "../components/SummaryCards";
import PnLChart from "../components/PnLChart";
import TradeTable from "../components/TradeTable";
import type { BotState, DailySummary, Trade } from "../types";

export default function DashboardPage() {
    const { data: state } = useData<BotState>("state", {
        positions: [], daily_pnl: 0, trading_day: null,
        trade_history: [], last_run: null,
    });
    const { data: summaries } = useData<DailySummary[]>("dailySummaries", []);
    const { data: trades } = useData<Trade[]>("trades", []);

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-white">Dashboard</h2>
                <span className="text-xs text-gray-500">
                    Last run: {state.last_run
                        ? new Date(state.last_run).toLocaleString()
                        : "Never"}
                </span>
            </div>
            <SummaryCards summaries={summaries} state={state} />
            <PnLChart summaries={summaries} />
            <div>
                <h3 className="text-sm font-medium text-gray-400 mb-3">
                    Recent Trades
                </h3>
                <TradeTable trades={trades} limit={10} />
            </div>
        </div>
    );
}
```

### 22. `dashboard/src/pages/PositionsPage.tsx`

```tsx
import { useData } from "../hooks/useData";
import PositionCard from "../components/PositionCard";
import type { BotState } from "../types";

export default function PositionsPage() {
    const { data: state } = useData<BotState>("state", {
        positions: [], daily_pnl: 0, trading_day: null,
        trade_history: [], last_run: null,
    });

    return (
        <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white">Open Positions</h2>
            {state.positions.length === 0 ? (
                <div className="bg-gray-900 rounded-xl border border-gray-800 p-12 text-center">
                    <p className="text-gray-500">No open positions</p>
                </div>
            ) : (
                <div className="grid grid-cols-3 gap-4">
                    {state.positions.map((pos) => (
                        <PositionCard key={pos.ticker} position={pos} />
                    ))}
                </div>
            )}
        </div>
    );
}
```

### 23. `dashboard/src/pages/TradeHistoryPage.tsx`

```tsx
import { useData } from "../hooks/useData";
import TradeTable from "../components/TradeTable";
import type { Trade } from "../types";

export default function TradeHistoryPage() {
    const { data: trades } = useData<Trade[]>("trades", []);

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-white">Trade History</h2>
                <span className="text-sm text-gray-500">
                    {trades.length} total trades
                </span>
            </div>
            <TradeTable trades={trades} />
        </div>
    );
}
```

### 24. `dashboard/src/pages/PerformancePage.tsx`

```tsx
import { useData } from "../hooks/useData";
import PerformanceCharts from "../components/PerformanceCharts";
import type { DailySummary, Trade } from "../types";

export default function PerformancePage() {
    const { data: summaries } = useData<DailySummary[]>("dailySummaries", []);
    const { data: trades } = useData<Trade[]>("trades", []);

    const closedTrades = trades.filter((t) => t.pnl !== null);
    const totalTrades = closedTrades.length;
    const wins = closedTrades.filter((t) => t.pnl! > 0).length;
    const losses = closedTrades.filter((t) => t.pnl! <= 0).length;
    const avgProfit =
        wins > 0
            ? closedTrades.filter((t) => t.pnl! > 0).reduce((s, t) => s + t.pnl!, 0) / wins
            : 0;
    const avgLoss =
        losses > 0
            ? closedTrades.filter((t) => t.pnl! <= 0).reduce((s, t) => s + t.pnl!, 0) / losses
            : 0;
    const bestTrade = closedTrades.length > 0
        ? Math.max(...closedTrades.map((t) => t.pnl!))
        : 0;
    const worstTrade = closedTrades.length > 0
        ? Math.min(...closedTrades.map((t) => t.pnl!))
        : 0;

    const stats = [
        { label: "Total Trades", value: `${totalTrades}` },
        { label: "Wins", value: `${wins}`, color: "text-emerald-400" },
        { label: "Losses", value: `${losses}`, color: "text-red-400" },
        {
            label: "Win Rate",
            value: totalTrades > 0 ? `${((wins / totalTrades) * 100).toFixed(1)}%` : "0%",
        },
        { label: "Avg Profit", value: `$${avgProfit.toFixed(2)}`, color: "text-emerald-400" },
        { label: "Avg Loss", value: `$${avgLoss.toFixed(2)}`, color: "text-red-400" },
        { label: "Best Trade", value: `$${bestTrade.toFixed(2)}`, color: "text-emerald-400" },
        { label: "Worst Trade", value: `$${worstTrade.toFixed(2)}`, color: "text-red-400" },
    ];

    return (
        <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white">Performance</h2>

            <div className="grid grid-cols-4 gap-4">
                {stats.map((stat) => (
                    <div
                        key={stat.label}
                        className="bg-gray-900 rounded-xl border border-gray-800 p-4"
                    >
                        <p className="text-xs text-gray-400 mb-1">
                            {stat.label}
                        </p>
                        <p
                            className={`text-xl font-bold ${
                                stat.color || "text-white"
                            }`}
                        >
                            {stat.value}
                        </p>
                    </div>
                ))}
            </div>

            <PerformanceCharts summaries={summaries} />
        </div>
    );
}
```

### 25. `dashboard/src/pages/ModelInsightsPage.tsx`

The AI showcase page. Shows Gemini's latest decisions with full context.

```tsx
import { useData } from "../hooks/useData";
import DecisionCard from "../components/DecisionCard";
import type { LatestDecisions } from "../types";

export default function ModelInsightsPage() {
    const { data } = useData<LatestDecisions>("latestDecisions", {
        run_time: null,
        decisions: [],
    });

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-white">
                    Model Insights
                </h2>
                <span className="text-sm text-gray-500">
                    Last analysis:{" "}
                    {data.run_time
                        ? new Date(data.run_time).toLocaleString()
                        : "Never"}
                </span>
            </div>

            {data.decisions.length === 0 ? (
                <div className="bg-gray-900 rounded-xl border border-gray-800 p-12 text-center">
                    <p className="text-gray-500">
                        No decisions yet — waiting for first bot run
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-3 gap-4">
                    {data.decisions.map((decision) => (
                        <DecisionCard
                            key={decision.ticker}
                            decision={decision}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
```

---

## Styling Rules (Apply Everywhere)

| Element | Tailwind Classes |
|---------|-----------------|
| Page background | `bg-gray-950` |
| Card | `bg-gray-900 rounded-xl border border-gray-800 p-6` |
| Card shadow (optional) | `shadow-lg` |
| Primary text | `text-gray-100` or `text-white` |
| Secondary text | `text-gray-400` |
| Muted text | `text-gray-500` |
| Profit / Positive | `text-emerald-400` |
| Loss / Negative | `text-red-400` |
| Neutral / Info | `text-blue-400` |
| BUY badge | `bg-emerald-900 text-emerald-300` |
| SELL badge | `bg-red-900 text-red-300` |
| HOLD badge | `bg-gray-700 text-gray-300` |
| Table row hover | `hover:bg-gray-800` |
| Table dividers | `divide-y divide-gray-800` |
| Chart grid lines | `stroke="#374151"` |
| Chart axis text | `stroke="#9CA3AF"` |

---

## Verification

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5173/trading-bot/` in your browser. You should see:

1. A dark-themed sidebar with 5 navigation links
2. The Dashboard page with 4 summary cards (all showing $0.00 / 0)
3. An empty P&L chart with "No data yet" message
4. An empty trades table with "No trades yet" message
5. All pages navigate correctly

The dashboard works with empty data. Once the bot starts running and populating data files, the dashboard will display real information.
