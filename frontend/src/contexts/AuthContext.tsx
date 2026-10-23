import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { User } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  currentUser: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    const cached = localStorage.getItem('leila_current_user');
    if (!cached) return null;
    try {
      return JSON.parse(cached) as User;
    } catch {
      localStorage.removeItem('leila_current_user');
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const token = localStorage.getItem('leila_auth_token');
      if (token) {
        const user = await api.auth.getCurrentUser();
        if (user) {
          localStorage.setItem('leila_current_user', JSON.stringify(user));
          setCurrentUser(user);
        } else {
          setCurrentUser(null);
        }
      } else {
        localStorage.removeItem('leila_current_user');
        setCurrentUser(null);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      // Clear invalid token
      localStorage.removeItem('leila_auth_token');
      localStorage.removeItem('leila_current_user');
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    try {
      const response = await api.auth.login(email, password);
      
      // Store token
      localStorage.setItem('leila_auth_token', response.access_token);
      
      // Get user info
      const user = await api.auth.getCurrentUser();
      if (!user) throw new Error('Login succeeded but user profile could not be loaded');
      localStorage.setItem('leila_current_user', JSON.stringify(user));
      setCurrentUser(user);
      
      return true;
    } catch (error: any) {
      console.error('Login failed:', error);
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('leila_auth_token');
    localStorage.removeItem('leila_current_user');
    setCurrentUser(null);
    api.auth.logout().catch(console.error);
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        isAuthenticated: !!currentUser,
        login,
        logout,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
