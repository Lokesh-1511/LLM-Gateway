import React, { useState } from 'react';
import Auth from './Auth';
import ChatPortal from './ChatPortal';
import AdminDashboard from './AdminDashboard';
import AdminSettings from './AdminSettings';
import { useAuth } from './useAuth';
import { LayoutDashboard, Settings } from 'lucide-react';

function App() {
  const { token, userRole, login, signup, logout } = useAuth();
  const [adminView, setAdminView] = useState('analytics'); // analytics or settings

  const handleLogin = async (isLogin, email, password, departmentId) => {
    if (isLogin) {
      return await login(email, password);
    } else {
      return await signup(email, password, departmentId);
    }
  };

  if (!token) {
    return <Auth onLogin={handleLogin} />;
  }

  if (userRole === 'admin') {
    return (
      <div className="min-h-screen bg-zinc-950">
        <div className="fixed top-20 right-6 z-50 bg-zinc-900 border border-zinc-800 rounded-lg shadow-lg overflow-hidden flex flex-col w-12">
          <button 
            onClick={() => setAdminView('analytics')}
            className={`p-3 flex justify-center hover:bg-zinc-800 transition-colors ${adminView === 'analytics' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-500'}`}
            title="Analytics"
          >
            <LayoutDashboard className="w-5 h-5" />
          </button>
          <div className="h-px bg-zinc-800 w-full" />
          <button 
            onClick={() => setAdminView('settings')}
            className={`p-3 flex justify-center hover:bg-zinc-800 transition-colors ${adminView === 'settings' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-500'}`}
            title="Settings"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
        {adminView === 'analytics' ? <AdminDashboard /> : <AdminSettings />}
      </div>
    );
  }

  // Otherwise, render the standard ChatPortal for normal users
  return <ChatPortal token={token} onLogout={logout} />;
}

export default App;
