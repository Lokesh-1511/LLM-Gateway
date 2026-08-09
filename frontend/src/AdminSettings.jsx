import React, { useState, useEffect } from 'react';
import { useAuth } from './useAuth';
import { Settings, Plus, UserPlus, Key, Server, Lock, CheckCircle2, Box, Shield } from 'lucide-react';

export default function AdminSettings() {
  const { token } = useAuth();
  
  const [departments, setDepartments] = useState([]);
  const [models, setModels] = useState([]);
  const [deptAccess, setDeptAccess] = useState({});
  
  const [deptName, setDeptName] = useState('');
  
  const [inviteEmail, setInviteEmail] = useState('');
  const [invitePassword, setInvitePassword] = useState('');
  const [inviteDept, setInviteDept] = useState('');
  
  const [newModel, setNewModel] = useState({
    display_name: '',
    provider_name: 'Groq',
    model_id_string: '',
    api_key: '',
    base_url: 'https://api.groq.com/openai/v1',
    is_active: true
  });
  
  const [status, setStatus] = useState({ type: '', message: '' });

  const fetchData = async () => {
    try {
      const depRes = await fetch('http://127.0.0.1:8000/api/departments');
      const deps = await depRes.json();
      setDepartments(deps);
      if (deps.length > 0 && !inviteDept) setInviteDept(deps[0].id);

      const modRes = await fetch('http://127.0.0.1:8000/api/models', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (modRes.ok) {
        const mods = await modRes.json();
        setModels(mods);
      }
      
      const accessObj = {};
      for (const d of deps) {
        const aRes = await fetch(`http://127.0.0.1:8000/api/departments/${d.id}/models`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (aRes.ok) {
          accessObj[d.id] = await aRes.json();
        }
      }
      setDeptAccess(accessObj);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token]);

  const showStatus = (type, message) => {
    setStatus({ type, message });
    setTimeout(() => setStatus({ type: '', message: '' }), 4000);
  };

  const handleCreateDept = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('http://127.0.0.1:8000/api/departments', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name: deptName })
      });
      if (res.ok) {
        showStatus('success', 'Department created successfully');
        setDeptName('');
        fetchData();
      } else {
        const error = await res.json();
        showStatus('error', error.detail || 'Failed to create department');
      }
    } catch (err) {
      showStatus('error', 'Network error');
    }
  };

  const handleInviteUser = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('http://127.0.0.1:8000/api/users/invite', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ email: inviteEmail, password: invitePassword, department_id: inviteDept })
      });
      if (res.ok) {
        showStatus('success', 'User invited successfully');
        setInviteEmail('');
        setInvitePassword('');
      } else {
        const error = await res.json();
        showStatus('error', error.detail || 'Failed to invite user');
      }
    } catch (err) {
      showStatus('error', 'Network error');
    }
  };

  const handleRegisterModel = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('http://127.0.0.1:8000/api/models', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(newModel)
      });
      if (res.ok) {
        showStatus('success', 'Model registered successfully');
        setNewModel({ ...newModel, display_name: '', model_id_string: '', api_key: '' });
        fetchData();
      } else {
        const error = await res.json();
        showStatus('error', error.detail || 'Failed to register model');
      }
    } catch (err) {
      showStatus('error', 'Network error');
    }
  };

  const handleToggleAccess = async (deptId, modelId) => {
    const currentAccess = deptAccess[deptId] || [];
    const newAccess = currentAccess.includes(modelId)
      ? currentAccess.filter(id => id !== modelId)
      : [...currentAccess, modelId];
      
    setDeptAccess({ ...deptAccess, [deptId]: newAccess });
    
    try {
      await fetch(`http://127.0.0.1:8000/api/departments/${deptId}/models`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ model_ids: newAccess })
      });
      showStatus('success', 'Access updated');
    } catch (err) {
      showStatus('error', 'Network error');
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 font-sans selection:bg-blue-500/30 py-8">
      <div className="max-w-6xl mx-auto px-6 space-y-8">
        
        <div className="flex items-center gap-3 border-b border-zinc-800 pb-4">
          <Settings className="w-6 h-6 text-zinc-400" />
          <h1 className="text-2xl font-bold tracking-tight">Enterprise Settings</h1>
        </div>

        {status.message && (
          <div className={`p-4 rounded-lg flex items-center gap-3 text-sm font-medium ${
            status.type === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 
            'bg-rose-500/10 text-rose-400 border border-rose-500/20'
          }`}>
            <CheckCircle2 className="w-5 h-5" />
            {status.message}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Register New Model */}
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
              <Box className="w-5 h-5 text-zinc-400" />
              Register AI Model
            </h2>
            <form onSubmit={handleRegisterModel} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Display Name</label>
                  <input type="text" value={newModel.display_name} onChange={e => setNewModel({...newModel, display_name: e.target.value})} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-zinc-600" placeholder="e.g. GPT-4o" required />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-400 mb-1">Provider Name</label>
                  <select value={newModel.provider_name} onChange={e => setNewModel({...newModel, provider_name: e.target.value})} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-zinc-600" required>
                    <option value="Groq">Groq</option>
                    <option value="OpenAI">OpenAI</option>
                    <option value="Anthropic">Anthropic</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Model ID (Upstream)</label>
                <input type="text" value={newModel.model_id_string} onChange={e => setNewModel({...newModel, model_id_string: e.target.value})} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-zinc-600" placeholder="e.g. gpt-4o-mini" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Base URL</label>
                <input type="text" value={newModel.base_url} onChange={e => setNewModel({...newModel, base_url: e.target.value})} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-zinc-600" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">API Key</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                  <input type="password" value={newModel.api_key} onChange={e => setNewModel({...newModel, api_key: e.target.value})} className="w-full pl-10 bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-zinc-600" placeholder="sk-..." required />
                </div>
              </div>
              <button type="submit" className="flex items-center justify-center gap-2 w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 rounded-md transition-colors text-sm">
                <Plus className="w-4 h-4" />
                Register Model
              </button>
            </form>
          </div>

          {/* Model Registry & Access Control */}
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl flex flex-col shadow-sm overflow-hidden">
            <div className="p-6 border-b border-zinc-800/60 bg-zinc-900/60 flex items-center gap-2">
              <Shield className="w-5 h-5 text-emerald-400" />
              <h2 className="text-lg font-semibold text-zinc-100">Model Access Governance</h2>
            </div>
            
            <div className="flex-1 overflow-y-auto p-0">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-zinc-950 border-b border-zinc-800/60 text-zinc-400">
                    <th className="px-5 py-3 font-medium">Department</th>
                    <th className="px-5 py-3 font-medium">Allowed Models</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {departments.map(dept => (
                    <tr key={dept.id} className="hover:bg-zinc-800/30 transition-colors">
                      <td className="px-5 py-4 font-medium text-zinc-200">{dept.name}</td>
                      <td className="px-5 py-4">
                        <div className="flex flex-wrap gap-3">
                          {models.map(model => (
                            <label key={model.id} className="flex items-center gap-2 cursor-pointer group">
                              <div className="relative flex items-center">
                                <input
                                  type="checkbox"
                                  className="peer sr-only"
                                  checked={deptAccess[dept.id]?.includes(model.id) || false}
                                  onChange={() => handleToggleAccess(dept.id, model.id)}
                                />
                                <div className="w-4 h-4 border border-zinc-600 rounded bg-zinc-900 peer-checked:bg-emerald-500 peer-checked:border-emerald-500 transition-colors flex items-center justify-center">
                                  {deptAccess[dept.id]?.includes(model.id) && (
                                    <CheckCircle2 className="w-3 h-3 text-white" />
                                  )}
                                </div>
                              </div>
                              <span className="text-sm text-zinc-400 group-hover:text-zinc-200 transition-colors">{model.display_name}</span>
                            </label>
                          ))}
                          {models.length === 0 && <span className="text-zinc-600 text-xs italic">No models registered</span>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* User Management */}
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
              <UserPlus className="w-5 h-5 text-zinc-400" />
              Invite User
            </h2>
            <form onSubmit={handleInviteUser} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Email Address</label>
                <input type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-zinc-600" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Password</label>
                <input type="password" value={invitePassword} onChange={(e) => setInvitePassword(e.target.value)} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-zinc-600" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Assign Department</label>
                <select value={inviteDept} onChange={(e) => setInviteDept(e.target.value)} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-zinc-600" required>
                  {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
              <button type="submit" className="flex items-center justify-center gap-2 w-full bg-zinc-800 hover:bg-zinc-700 text-zinc-100 font-medium py-2 rounded-md transition-colors text-sm">
                <UserPlus className="w-4 h-4" /> Send Invite
              </button>
            </form>
          </div>

          {/* Department Management */}
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
              <Server className="w-5 h-5 text-zinc-400" />
              Add Department
            </h2>
            <form onSubmit={handleCreateDept} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Department Name</label>
                <input type="text" value={deptName} onChange={(e) => setDeptName(e.target.value)} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-zinc-600" required />
              </div>
              <button type="submit" className="flex items-center justify-center gap-2 w-full bg-zinc-100 hover:bg-white text-zinc-900 font-medium py-2 rounded-md transition-colors text-sm">
                <Plus className="w-4 h-4" /> Create Department
              </button>
            </form>
          </div>

        </div>
      </div>
    </div>
  );
}
