"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

export interface User {
  name: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  login: async () => {},
  signup: async () => {},
  logout: () => {},
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Check for existing session token in localStorage on mount
    const checkSession = () => {
      try {
        const token = localStorage.getItem("gammalens_token");
        const storedUser = localStorage.getItem("gammalens_user");
        
        if (token && storedUser) {
          setUser(JSON.parse(storedUser));
        }
      } catch (error) {
        console.error("Failed to parse stored user", error);
        localStorage.removeItem("gammalens_token");
        localStorage.removeItem("gammalens_user");
      } finally {
        setIsLoading(false);
      }
    };

    checkSession();
  }, []);

  const login = async (email: string, password: string): Promise<void> => {
    // Mock API call
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (email && password.length >= 8) {
          const mockUser = { name: email.split("@")[0] || "User", email };
          setUser(mockUser);
          localStorage.setItem("gammalens_token", "mock_jwt_token_123");
          localStorage.setItem("gammalens_user", JSON.stringify(mockUser));
          resolve();
        } else {
          reject(new Error("Invalid email or password. Password must be at least 8 characters."));
        }
      }, 1200); // Simulate network latency
    });
  };

  const signup = async (name: string, email: string, password: string): Promise<void> => {
    // Mock API call
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (name && email && password.length >= 8) {
          const mockUser = { name, email };
          setUser(mockUser);
          localStorage.setItem("gammalens_token", "mock_jwt_token_123");
          localStorage.setItem("gammalens_user", JSON.stringify(mockUser));
          resolve();
        } else {
          reject(new Error("Invalid input. Please check your details and try again."));
        }
      }, 1500); // Simulate network latency
    });
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("gammalens_token");
    localStorage.removeItem("gammalens_user");
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
