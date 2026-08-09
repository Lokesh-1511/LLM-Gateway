import React, { useState, useEffect } from 'react';
import { useAuth } from './useAuth';
import { DollarSign, ShieldAlert, Zap, LogOut, Server, Activity, BarChart2, Filter } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, AreaChart, Area } from 'recharts';

export default function AdminDashboard() {
  const { token, logout } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('All');

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/analytics/summary', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        setAnalytics(data);
        setLoading(false);
      });
  }, [token]);

  if (loading || !analytics) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center text-zinc-400">
        <Activity className="w-6 h-6 animate-spin" />
        <span className="ml-3 text-sm font-medium tracking-wide">Loading Enterprise Telemetry...</span>
      </div>
    );
  }

  const PIICOLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];
  
  // Prepare data for recharts
  const modelDist = analytics.model_distribution || [];
  const deptSpend = analytics.department_spend || [];
  const timeSeries = analytics.time_series_data || [];

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 font-sans selection:bg-blue-500/30">
      
      {/* Navigation Bar */}
      <nav className="border-b border-zinc-800/60 bg-zinc-950/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-zinc-800 to-zinc-700 border border-zinc-700 flex items-center justify-center shadow-lg">
              <BarChart2 className="w-4 h-4 text-zinc-300" />
            </div>
            <span className="font-semibold text-zinc-100 tracking-tight">PromptOps <span className="text-zinc-500 font-normal">| Orchestration</span></span>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-md px-3 py-1.5">
              <Filter className="w-3.5 h-3.5 text-zinc-400" />
              <select 
                value={filter}
                onChange={e => setFilter(e.target.value)}
                className="bg-transparent text-sm text-zinc-200 focus:outline-none"
              >
                <option value="All">Global (All Departments)</option>
                <option value="Engineering">Engineering</option>
                <option value="Sales">Sales</option>
              </select>
            </div>
            <button 
              onClick={logout}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-zinc-800/50 text-zinc-400 hover:text-zinc-100 transition-colors text-sm font-medium"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        
        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-zinc-400">Total Pipeline Cost</h3>
              <div className="p-2 bg-emerald-500/10 rounded-md">
                <DollarSign className="w-4 h-4 text-emerald-400" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-zinc-100">${(deptSpend.reduce((acc, d) => acc + d.cost, 0)).toFixed(4)}</span>
            </div>
            <p className="text-xs text-emerald-500/80 mt-2 font-medium">Saved ${analytics.money_saved.toFixed(2)} via caching</p>
          </div>

          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-zinc-400">Governance & Security</h3>
              <div className="p-2 bg-rose-500/10 rounded-md">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-zinc-100">{analytics.total_pii_blocked + analytics.total_policy_violations}</span>
            </div>
            <p className="text-xs text-rose-500/80 mt-2 font-medium">Threats Intercepted</p>
          </div>

          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-zinc-400">Total Interactions</h3>
              <div className="p-2 bg-blue-500/10 rounded-md">
                <Zap className="w-4 h-4 text-blue-400" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-zinc-100">{analytics.total_requests}</span>
            </div>
            <p className="text-xs text-blue-400/80 mt-2 font-medium">Across all mapped models</p>
          </div>
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Model Usage Pie Chart */}
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-5 shadow-sm flex flex-col">
            <h3 className="text-sm font-semibold text-zinc-100 mb-2">Model Request Distribution</h3>
            <div className="flex-1 min-h-[300px] w-full">
              {modelDist.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={modelDist}
                      cx="50%" cy="50%" innerRadius={70} outerRadius={100} paddingAngle={5}
                      dataKey="requests" nameKey="name" stroke="none"
                    >
                      {modelDist.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={PIICOLORS[index % PIICOLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', color: '#f4f4f5' }} itemStyle={{ color: '#f4f4f5' }} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-zinc-500 text-sm">No model data available.</div>
              )}
            </div>
          </div>

          {/* Department Token Spend Stacked Bar */}
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-5 shadow-sm flex flex-col">
            <h3 className="text-sm font-semibold text-zinc-100 mb-2">Token Spend by Department</h3>
            <div className="flex-1 min-h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={deptSpend} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="department" stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', color: '#f4f4f5' }} cursor={{fill: '#27272a', opacity: 0.4}} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                  <Bar dataKey="tokens" name="Tokens Used" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="cost" name="Estimated Cost ($)" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Charts Row 2 */}
        <div className="grid grid-cols-1 gap-6">
          {/* Time Series Latency Line Chart */}
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-zinc-100 mb-6 flex items-center gap-2">
              System Latency Over 24h
            </h3>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorLatency" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="time" stroke="#71717a" fontSize={10} tickFormatter={(val) => val.split(' ')[1]} tickLine={false} axisLine={false} />
                  <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', color: '#f4f4f5' }} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                  <Area type="monotone" dataKey="avg_latency" name="Avg Latency (ms)" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorLatency)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
