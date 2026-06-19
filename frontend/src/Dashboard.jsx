import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Activity, 
  ShieldAlert, 
  Zap, 
  RefreshCcw, 
  Terminal, 
  Server, 
  Database,
  CheckCircle2,
  XCircle
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from 'recharts';

export default function Dashboard() {
  const [data, setData] = useState({
    total_requests: 0,
    total_pii_blocked: 0,
    total_savings: 0,
    recent_logs: []
  });
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      // Assuming Vite dev server proxy or direct CORS enabled on FastAPI
      const response = await axios.get('http://localhost:8000/api/analytics/summary');
      setData(response.data);
    } catch (error) {
      console.error("Failed to fetch analytics:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    // Optional: Refresh every 30 seconds
    const interval = setInterval(fetchAnalytics, 30000);
    return () => clearInterval(interval);
  }, []);

  // Format data for the chart (reverse to show chronological left-to-right)
  const chartData = [...data.recent_logs].reverse().map((log, index) => ({
    name: `Req ${index + 1}`,
    tokens: log.token_count,
    cacheHit: log.was_cache_hit,
    timestamp: new Date(log.timestamp).toLocaleTimeString()
  }));

  const formatCurrency = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 6 }).format(val);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans selection:bg-zinc-800">
      {/* Top Navigation */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-950/50 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <Terminal className="w-5 h-5 text-zinc-400" />
          <h1 className="text-sm font-semibold tracking-wide text-zinc-100">PromptOps Gateway</h1>
          <div className="flex items-center gap-2 ml-4 px-2.5 py-1 rounded-full bg-zinc-900 border border-zinc-800">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-medium text-zinc-400">System Online</span>
          </div>
        </div>
        <button 
          onClick={fetchAnalytics}
          disabled={loading}
          className="p-2 hover:bg-zinc-800 rounded-md transition-colors border border-transparent hover:border-zinc-700"
        >
          <RefreshCcw className={`w-4 h-4 text-zinc-400 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </nav>

      <main className="max-w-7xl mx-auto p-6 space-y-6">
        
        {/* Top Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <MetricCard 
            title="Total Requests" 
            value={data.total_requests} 
            icon={<Activity className="w-4 h-4 text-zinc-400" />} 
          />
          <MetricCard 
            title="PII Threats Blocked" 
            value={data.total_pii_blocked} 
            icon={<ShieldAlert className="w-4 h-4 text-red-500/80" />} 
            valueClass="text-red-400"
          />
          <MetricCard 
            title="Gateway Savings" 
            value={formatCurrency(data.total_savings)} 
            icon={<Zap className="w-4 h-4 text-emerald-500/80" />} 
            valueClass="text-emerald-400"
          />
        </div>

        {/* Main Content Two Columns */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column - Chart */}
          <div className="lg:col-span-2 border border-zinc-800 bg-zinc-900/20 rounded-lg p-6">
            <div className="mb-6">
              <h2 className="text-sm font-medium text-zinc-100">Usage Activity</h2>
              <p className="text-xs text-zinc-500 mt-1">Token consumption over recent requests</p>
            </div>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis 
                    dataKey="name" 
                    stroke="#52525b" 
                    fontSize={10} 
                    tickLine={false} 
                    axisLine={false} 
                    dy={10}
                  />
                  <YAxis 
                    stroke="#52525b" 
                    fontSize={10} 
                    tickLine={false} 
                    axisLine={false} 
                    dx={-10}
                  />
                  <Tooltip 
                    cursor={{fill: '#27272a', opacity: 0.4}}
                    contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', fontSize: '12px' }}
                    itemStyle={{ color: '#e4e4e7' }}
                  />
                  <Bar dataKey="tokens" radius={[2, 2, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.cacheHit ? '#10b981' : '#3f3f46'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex gap-4 mt-4 text-xs text-zinc-500 justify-end">
              <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-zinc-600"></div> Live API</div>
              <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-emerald-500"></div> Cache Hit</div>
            </div>
          </div>

          {/* Right Column - Status */}
          <div className="border border-zinc-800 bg-zinc-900/20 rounded-lg p-6">
            <div className="mb-6">
              <h2 className="text-sm font-medium text-zinc-100">Gateway Status</h2>
              <p className="text-xs text-zinc-500 mt-1">Component health check</p>
            </div>
            <div className="space-y-4">
              <StatusRow title="Presidio PII Firewall" icon={<ShieldAlert className="w-4 h-4" />} online={true} />
              <StatusRow title="ChromaDB Semantic Cache" icon={<Database className="w-4 h-4" />} online={true} />
              <StatusRow title="Groq Outbound Router" icon={<Server className="w-4 h-4" />} online={true} />
            </div>
          </div>
        </div>

        {/* Logs Table */}
        <div className="border border-zinc-800 bg-zinc-900/20 rounded-lg overflow-hidden">
          <div className="px-6 py-5 border-b border-zinc-800">
            <h2 className="text-sm font-medium text-zinc-100">Recent API Logs</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-zinc-800 text-xs font-medium text-zinc-500 bg-zinc-900/50">
                  <th className="px-6 py-3 font-medium">Timestamp</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Prompt Snippet</th>
                  <th className="px-6 py-3 font-medium text-right">Tokens</th>
                  <th className="px-6 py-3 font-medium text-right">Latency</th>
                </tr>
              </thead>
              <tbody className="text-sm divide-y divide-zinc-800/50">
                {data.recent_logs.map((log) => (
                  <tr key={log.id} className="hover:bg-zinc-900/50 transition-colors group">
                    <td className="px-6 py-3 text-zinc-400 text-xs font-mono">
                      {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="px-6 py-3">
                      {log.was_cache_hit ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          CACHE
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                          LIVE
                        </span>
                      )}
                      {log.was_pii_detected && (
                        <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-red-500/10 text-red-400 border border-red-500/20">
                          PII
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-3 text-zinc-300 max-w-xs truncate">
                      {log.original_prompt}
                    </td>
                    <td className="px-6 py-3 text-right text-zinc-400 font-mono text-xs">
                      {log.token_count}
                    </td>
                    <td className="px-6 py-3 text-right text-zinc-400 font-mono text-xs">
                      {log.latency_ms.toFixed(0)}ms
                    </td>
                  </tr>
                ))}
                {data.recent_logs.length === 0 && (
                  <tr>
                    <td colSpan="5" className="px-6 py-8 text-center text-sm text-zinc-500">
                      No request logs available. Send a prompt to populate the dashboard.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}

function MetricCard({ title, value, icon, valueClass = "text-zinc-100" }) {
  return (
    <div className="p-6 rounded-lg border border-zinc-800 bg-zinc-900/20 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-medium text-zinc-500">{title}</h3>
        {icon}
      </div>
      <div className={`text-3xl font-light tracking-tight ${valueClass}`}>
        {value}
      </div>
    </div>
  );
}

function StatusRow({ title, icon, online }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-zinc-800/50 last:border-0">
      <div className="flex items-center gap-3">
        <div className="text-zinc-500">{icon}</div>
        <span className="text-xs text-zinc-300">{title}</span>
      </div>
      {online ? (
        <CheckCircle2 className="w-4 h-4 text-emerald-500/80" />
      ) : (
        <XCircle className="w-4 h-4 text-red-500/80" />
      )}
    </div>
  );
}
