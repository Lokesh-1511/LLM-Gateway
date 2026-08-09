import React, { useState, useEffect } from 'react';
import { useAuth } from './useAuth';
import { 
  DollarSign, 
  ShieldAlert, 
  Zap, 
  LogOut, 
  Server,
  Activity,
  AlertOctagon
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

export default function AdminDashboard() {
  const { token, logout } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

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

  const PIICOLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 font-sans selection:bg-blue-500/30">
      
      {/* Navigation Bar */}
      <nav className="border-b border-zinc-800/60 bg-zinc-950/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-zinc-800 to-zinc-700 border border-zinc-700 flex items-center justify-center shadow-lg">
              <Server className="w-4 h-4 text-zinc-300" />
            </div>
            <span className="font-semibold text-zinc-100 tracking-tight">PromptOps <span className="text-zinc-500 font-normal">| Enterprise ROI</span></span>
          </div>
          <button 
            onClick={logout}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-zinc-800/50 text-zinc-400 hover:text-zinc-100 transition-colors text-sm font-medium"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        
        {/* KPI Cards (Top Row) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          {/* Financial Impact */}
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-5 shadow-sm hover:border-zinc-700/60 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-zinc-400">Financial Impact (Total Savings)</h3>
              <div className="p-2 bg-emerald-500/10 rounded-md">
                <DollarSign className="w-4 h-4 text-emerald-400" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-zinc-100">${analytics.money_saved.toFixed(2)}</span>
            </div>
            <p className="text-xs text-emerald-500/80 mt-2 font-medium">
              +{analytics.savings_percentage.toFixed(1)}% Tokens Saved
            </p>
          </div>

          {/* Security Health */}
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-5 shadow-sm hover:border-zinc-700/60 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-zinc-400">Total Threats Blocked</h3>
              <div className="p-2 bg-rose-500/10 rounded-md">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-zinc-100">{analytics.total_pii_blocked + analytics.total_policy_violations}</span>
            </div>
            <p className="text-xs text-rose-500/80 mt-2 font-medium">
              {analytics.total_pii_blocked} PII • {analytics.total_policy_violations} Policy
            </p>
          </div>

          {/* Cache Efficiency */}
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-5 shadow-sm hover:border-zinc-700/60 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-zinc-400">Cache Hit Rate</h3>
              <div className="p-2 bg-blue-500/10 rounded-md">
                <Zap className="w-4 h-4 text-blue-400" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-zinc-100">{analytics.cache_hit_rate.toFixed(1)}%</span>
            </div>
            <p className="text-xs text-blue-400/80 mt-2 font-medium">
              Across {analytics.total_requests} total requests
            </p>
          </div>

        </div>

        {/* Charts (Middle Row) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Bar Chart: Department Usage */}
          <div className="lg:col-span-2 bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-zinc-100 mb-6 flex items-center gap-2">
              Tokens Saved vs. Used (By Department)
            </h3>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.department_stats} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="department" stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px', color: '#f4f4f5' }}
                    itemStyle={{ color: '#f4f4f5' }}
                    cursor={{fill: '#27272a', opacity: 0.4}}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                  <Bar dataKey="tokens_used" name="Tokens Used" stackId="a" fill="#3f3f46" radius={[0, 0, 4, 4]} />
                  <Bar dataKey="tokens_saved" name="Tokens Saved" stackId="a" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Pie Chart: PII Distribution */}
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-5 shadow-sm flex flex-col">
            <h3 className="text-sm font-semibold text-zinc-100 mb-2 flex items-center gap-2">
              PII Threat Distribution
            </h3>
            <div className="flex-1 min-h-[250px] w-full flex items-center justify-center">
              {analytics.pii_stats && analytics.pii_stats.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={analytics.pii_stats}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                      stroke="none"
                    >
                      {analytics.pii_stats.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={PIICOLORS[index % PIICOLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px', color: '#f4f4f5' }}
                      itemStyle={{ color: '#f4f4f5' }}
                    />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-zinc-500 text-sm flex flex-col items-center gap-2">
                  <ShieldAlert className="w-8 h-8 opacity-20" />
                  No PII threats detected yet.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Audit Log (Bottom Row) */}
        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl overflow-hidden shadow-sm">
          <div className="px-5 py-4 border-b border-zinc-800/60 flex items-center gap-2">
            <AlertOctagon className="w-4 h-4 text-rose-400" />
            <h3 className="text-sm font-semibold text-zinc-100">Recent Policy Violations</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-zinc-900/20 text-xs font-medium text-zinc-500 uppercase tracking-wider">
                  <th className="px-5 py-3 border-b border-zinc-800/60 w-1/3">Violated Policy</th>
                  <th className="px-5 py-3 border-b border-zinc-800/60">Original Prompt Context</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 text-sm">
                {analytics.recent_violations && analytics.recent_violations.length > 0 ? (
                  analytics.recent_violations.map((viol, i) => (
                    <tr key={i} className="hover:bg-zinc-800/20 transition-colors">
                      <td className="px-5 py-3 text-rose-400/90 font-medium whitespace-nowrap">
                        {viol.policy}
                      </td>
                      <td className="px-5 py-3 text-zinc-300 max-w-lg truncate">
                        "{viol.prompt}"
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={2} className="px-5 py-8 text-center text-zinc-500 text-sm">
                      No recent policy violations found.
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
