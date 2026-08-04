import React from 'react';
import Auth from './Auth';
import ChatPortal from './ChatPortal';
import { useAuth } from './useAuth';

function App() {
  const { token, login, signup, logout } = useAuth();

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

  return <ChatPortal token={token} onLogout={logout} />;
}

export default App;
