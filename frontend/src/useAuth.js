import { useState, useEffect } from 'react';

export function useAuth() {
  const [token, setToken] = useState(localStorage.getItem('access_token'));
  const [userRole, setUserRole] = useState(localStorage.getItem('user_role'));

  useEffect(() => {
    if (token) {
      localStorage.setItem('access_token', token);
    } else {
      localStorage.removeItem('access_token');
    }
    
    if (userRole) {
      localStorage.setItem('user_role', userRole);
    } else {
      localStorage.removeItem('user_role');
    }
  }, [token, userRole]);

  const login = async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const res = await fetch('http://127.0.0.1:8000/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });
    
    if (res.ok) {
      const data = await res.json();
      setToken(data.access_token);
      setUserRole(data.role);
      return true;
    }
    return false;
  };

  const signup = async (email, password, department_id) => {
    const res = await fetch('http://127.0.0.1:8000/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, department_id }),
    });
    
    if (res.ok) {
      // automatically login after signup
      return await login(email, password);
    }
    return false;
  };

  const logout = () => {
    setToken(null);
    setUserRole(null);
  };

  return { token, userRole, login, signup, logout };
}
