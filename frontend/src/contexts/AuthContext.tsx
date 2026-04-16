/**
 * Authentication Context - User session management
 */

"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '@/lib/api';

interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'signer' | 'viewer';
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  loading: boolean;
  login: (emailOrData: string | any, password?: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (email: string, password: string, fullName: string, role?: string) => Promise<void>;
  checkAuth: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const STORAGE_KEYS = {
  ACCESS_TOKEN: 'orgon_access_token',
  REFRESH_TOKEN: 'orgon_refresh_token',
  USER: 'orgon_user',
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  // Mark as mounted (client-side only)
  useEffect(() => {
    setMounted(true);
  }, []);

  // Load session from localStorage on mount (client-side only)
  useEffect(() => {
    if (!mounted || typeof window === 'undefined') return;
    
    try {
      const storedAccessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
      const storedRefreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
      const storedUser = localStorage.getItem(STORAGE_KEYS.USER);

      if (storedAccessToken && storedRefreshToken && storedUser) {
        setAccessToken(storedAccessToken);
        setRefreshToken(storedRefreshToken);
        setUser(JSON.parse(storedUser));
        
        // Verify token is still valid
        checkAuth().finally(() => setLoading(false));
      } else {
        setLoading(false);
      }
    } catch (error) {
      console.error('Failed to load session:', error);
      setLoading(false);
    }
  }, [mounted]);

  const saveSession = (access: string, refresh: string, userData: User) => {
    if (typeof window === 'undefined') return;
    
    try {
      localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, access);
      localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refresh);
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(userData));
      
      // Also save to cookies for middleware
      document.cookie = `orgon_access_token=${access}; path=/; max-age=${60 * 60 * 24 * 7}`; // 7 days
      document.cookie = `orgon_refresh_token=${refresh}; path=/; max-age=${60 * 60 * 24 * 30}`; // 30 days
      
      setAccessToken(access);
      setRefreshToken(refresh);
      setUser(userData);
    } catch (error) {
      console.error('Failed to save session:', error);
    }
  };

  const clearSession = () => {
    if (typeof window === 'undefined') return;
    
    try {
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.USER);
      
      // Also clear cookies
      document.cookie = 'orgon_access_token=; path=/; max-age=0';
      document.cookie = 'orgon_refresh_token=; path=/; max-age=0';
      
      setAccessToken(null);
      setRefreshToken(null);
      setUser(null);
    } catch (error) {
      console.error('Failed to clear session:', error);
    }
  };

  const login = async (emailOrData: string | any, password?: string) => {
    // Support both signatures:
    // 1. login(email, password) - old way
    // 2. login(responseData) - new way with already fetched data
    
    if (typeof emailOrData === 'string' && password) {
      // Old signature: email + password
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: emailOrData, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      saveSession(data.access_token, data.refresh_token, data.user);
    } else {
      // New signature: response data object
      const data = emailOrData;
      saveSession(data.access_token, data.refresh_token, data.user);
    }
  };

  const register = async (email: string, password: string, fullName: string, role: string = 'viewer') => {
    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        email, 
        password, 
        full_name: fullName,
        role 
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }

    // After successful registration, auto-login
    await login(email, password);
  };

  const logout = async () => {
    if (refreshToken) {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch (error) {
        console.error('Logout API call failed:', error);
      }
    }

    clearSession();
  };

  const checkAuth = async (): Promise<boolean> => {
    if (!accessToken) {
      return false;
    }

    try {
      const response = await fetch('/api/auth/me', {
        headers: { 
          'Authorization': `Bearer ${accessToken}` 
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        return true;
      } else if (response.status === 401 && refreshToken) {
        // Try to refresh token
        const refreshResponse = await fetch('/api/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshResponse.ok) {
          const data = await refreshResponse.json();
          saveSession(data.access_token, data.refresh_token, user!);
          return true;
        }
      }

      clearSession();
      return false;
    } catch (error) {
      console.error('Auth check failed:', error);
      clearSession();
      return false;
    }
  };

  const value = {
    user,
    accessToken,
    refreshToken,
    loading,
    login,
    logout,
    register,
    checkAuth,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

export default AuthContext;
