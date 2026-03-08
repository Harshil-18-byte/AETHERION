"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { signup } = useAuth();
  const router = useRouter();

  const validateForm = () => {
    // Check missing fields
    if (!name || !email || !password || !confirmPassword) {
      setError("Please fill in all fields.");
      return false;
    }
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError("Please enter a valid email format.");
      return false;
    }
    
    // Password length validation
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return false;
    }
    
    // Password match validation
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return false;
    }
    
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");

    if (!validateForm()) {
      setIsSubmitting(false);
      return;
    }

    try {
      await signup(name, email, password);
      // redirect to dashboard on success
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create account");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-brand">
            GammaLens<span className="auth-brand-subtitle">Options Market Intelligence</span>
          </div>
          <div className="auth-tagline">Create Account</div>
        </div>

        {error && <div className="auth-global-error">{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-field">
            <label className="auth-label" htmlFor="name">Full Name</label>
            <input
              id="name"
              type="text"
              className={`auth-input ${error && !name ? 'has-error' : ''}`}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="John Doe"
              disabled={isSubmitting}
            />
          </div>

          <div className="auth-field">
            <label className="auth-label" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              className={`auth-input ${error && !email ? 'has-error' : ''}`}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              disabled={isSubmitting}
            />
          </div>

          <div className="auth-field">
            <label className="auth-label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className={`auth-input ${(error && !password) || (error && password !== confirmPassword) ? 'has-error' : ''}`}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={isSubmitting}
            />
          </div>

          <div className="auth-field">
            <label className="auth-label" htmlFor="confirmPassword">Confirm Password</label>
            <input
              id="confirmPassword"
              type="password"
              className={`auth-input ${(error && !confirmPassword) || (error && password !== confirmPassword) ? 'has-error' : ''}`}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              disabled={isSubmitting}
            />
          </div>

          <button 
            type="submit" 
            className="auth-button"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <div className="auth-footer">
          Already have an account? 
          <Link href="/login" className="auth-link">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
