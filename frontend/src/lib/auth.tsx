'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authApi, User } from './api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (orgName: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'ledgerly_token';

// DEV MODE - Bypass login/register UI, use real token for API calls
const DEV_MODE = true;

// Real token from existing user - all API calls use real backend data
const DEV_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZWNhOWM5ZmItNTQ0ZS00ZTkwLWFlMmItYTc3YzRlMTdjZTVkIiwib3JnX2lkIjoiY2IyYmE4NGMtMWJhOS00MDExLWIxYzMtNDBjYTk0OGIzZThlIiwiZW1haWwiOiJkZW1vQGxlZGdlcmx5LmFwcCIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3MDU2NTUzN30.Wm0Zow6yo5LXZcnHos3tMx2BFtKlFMbSILwK9-X9M-0';

const DEV_USER: User = {
  id: 'eca9c9fb-544e-4e90-ae2b-a77c4e17ce5d',
  org_id: 'cb2ba84c-1ba9-4011-b1c3-40ca948b3e8e',
  email: 'demo@ledgerly.app',
  role: 'admin',
  created_at: new Date().toISOString(),
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(DEV_MODE ? DEV_USER : null);
  const [token, setToken] = useState<string | null>(DEV_MODE ? DEV_TOKEN : null);
  const [isLoading, setIsLoading] = useState(!DEV_MODE);

  useEffect(() => {
    if (DEV_MODE) {
      // Dev mode: always use real token, skip login UI
      setUser(DEV_USER);
      setToken(DEV_TOKEN);
      setIsLoading(false);
      return;
    }

    const storedToken = localStorage.getItem(TOKEN_KEY);
    if (storedToken) {
      setToken(storedToken);
      authApi.me(storedToken)
        .then(setUser)
        .catch(() => {
          localStorage.removeItem(TOKEN_KEY);
          setToken(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    if (DEV_MODE) {
      setUser(DEV_USER);
      setToken(DEV_TOKEN);
      return;
    }
    const response = await authApi.login(email, password);
    localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    const userData = await authApi.me(response.access_token);
    setUser(userData);
  };

  const register = async (orgName: string, email: string, password: string) => {
    if (DEV_MODE) {
      setUser(DEV_USER);
      setToken(DEV_TOKEN);
      return;
    }
    const response = await authApi.register(orgName, email, password);
    localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    const userData = await authApi.me(response.access_token);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    if (DEV_MODE) {
      setToken(DEV_TOKEN);
      setUser(DEV_USER);
    } else {
      setToken(null);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
