import React from 'react';
import Auth from './Auth';
import ChatPortal from './ChatPortal';
import AdminDashboard from './AdminDashboard';
import { useAuth } from './useAuth';

function App() {
  const { token, userRole, login, signup, logout } = useAuth();

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

  // If the user is an admin, render the new Enterprise ROI Dashboard
  if (userRole === 'admin') {
    return <AdminDashboard />;
  }

  // Otherwise, render the standard ChatPortal for normal users
  return <ChatPortal token={token} onLogout={logout} />;
}

export default App;
