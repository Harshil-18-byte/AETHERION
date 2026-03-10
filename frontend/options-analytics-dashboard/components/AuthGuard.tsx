"use client";

import { useRouter, usePathname } from "next/navigation";
import { useAuth, BYPASS_AUTH } from "@/contexts/AuthContext";
import React, { useEffect } from "react";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // If auth state has loaded and user is not authenticated, redirect to login
    if (!isLoading && !isAuthenticated && !BYPASS_AUTH) {
      // Allow access to auth pages
      if (pathname !== "/login" && pathname !== "/signup") {
        router.push("/login");
      }
    }
  }, [isAuthenticated, isLoading, router, pathname]);

  if (BYPASS_AUTH) return <>{children}</>;

  // Show nothing while loading to prevent flash of content before redirect
  if (isLoading) {
    return (
      <div className="loading-container">
        <span className="loading-brand">GammaLens</span>
        <div className="loading-bar"><div className="loading-bar-inner" /></div>
        <span className="loading-text">Verifying session...</span>
      </div>
    );
  }

  // If not authenticated and not on an auth page, don't render children
  // (The useEffect will handle the redirect)
  if (!isAuthenticated && pathname !== "/login" && pathname !== "/signup") {
    return null;
  }

  return <>{children}</>;
}
