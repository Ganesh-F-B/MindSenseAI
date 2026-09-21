"use client";
import { createContext, useContext, useState, useEffect } from 'react';
import Cookies from 'js-cookie';
import api from '../lib/api';
import { useRouter } from 'next/navigation';

interface User {
  id: number;
  email: string;
  full_name: string;
  phone_number: string;
  emergency_contacts: any[];
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

const getStoredToken = () => {
  if (typeof window === 'undefined') return null;
  return Cookies.get('token') || window.localStorage.getItem('token');
};

const persistToken = (token: string) => {
  Cookies.set('token', token, { expires: 7, path: '/' });
  if (typeof window !== 'undefined') {
    window.localStorage.setItem('token', token);
  }
};

const clearStoredToken = () => {
  Cookies.remove('token', { path: '/' });
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem('token');
  }
};

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const checkAuth = async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const res = await api.get('/users/me');
      setUser(res.data);
    } catch (err) {
      clearStoredToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const login = async (token: string) => {
    persistToken(token);
    await checkAuth();
    router.push('/dashboard');
  };

  const logout = () => {
    clearStoredToken();
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
