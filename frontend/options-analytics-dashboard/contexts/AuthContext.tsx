"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: number;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (full_name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// --- TEMPORARY BYPASS TOGGLE ---
export const BYPASS_AUTH = true;
// -------------------------------

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMounted, setIsMounted] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const logout = useCallback(() => {
    localStorage.getItem("optix_token");
    localStorage.removeItem("optix_token");
    setToken(null);
    setUser(null);
  }, []);

  const fetchUserProfile = useCallback(async (authToken: string) => {
    if (BYPASS_AUTH || authToken === "dummy_token_for_dev") {
      setUser({
        id: 1,
        email: "dev@example.com",
        full_name: "Mock User",
        is_active: 1
      });
      setIsLoading(false);
      return;
    }
    
    try {
      const response = await fetch(`${API_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        logout();
      }
    } catch (error) {
      console.error("Failed to fetch user profile:", error);
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [API_URL, logout]);

  useEffect(() => {
    setIsMounted(true);
    
    // --- TEMPORARY BYPASS ---
    if (BYPASS_AUTH) {
      const dummyToken = "dummy_token_for_dev";
      const dummyUser = {
          id: 1,
          email: "dev@example.com",
          full_name: "Mock User",
          is_active: 1
      };
      setToken(dummyToken);
      setUser(dummyUser);
      setIsLoading(false);
      return;
    }
    // ------------------------

    const storedToken = localStorage.getItem("optix_token");
    if (storedToken) {
      setToken(storedToken);
      fetchUserProfile(storedToken);
    } else {
      setIsLoading(false);
    }
  }, [fetchUserProfile]);

  const login = async (email: string, password: string) => {
    if (BYPASS_AUTH) {
      console.log("Mock login for:", email);
      const dummyToken = "dummy_token_for_dev";
      const dummyUser = {
          id: 1,
          email: email || "dev@example.com",
          full_name: "Mock User",
          is_active: 1
      };
      localStorage.setItem("optix_token", dummyToken);
      setToken(dummyToken);
      setUser(dummyUser);
      setIsLoading(false);
      return;
    }

    const formData = new URLSearchParams();
    formData.append("username", email); // OAuth2PasswordRequestForm expects 'username'
    formData.append("password", password);

    const response = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Login failed");
    }

    const { access_token } = await response.json();
    localStorage.setItem("optix_token", access_token);
    setToken(access_token);
    await fetchUserProfile(access_token);
  };

  const signup = async (full_name: string, email: string, password: string) => {
    if (BYPASS_AUTH) {
      await login(email, password);
      return;
    }

    const response = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ full_name, email, password }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Signup failed");
    }

    // After signup, automatically log the user in
    await login(email, password);
  };

  const isAuthenticated = !!user;

  if (!isMounted) return null;

  return (
    <AuthContext.Provider
      value={{ user, token, isAuthenticated, login, signup, logout, isLoading }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
