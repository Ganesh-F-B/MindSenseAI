"use client";
import { useState } from "react";
import api from "../../lib/api";
import { useAuth } from "../../hooks/useAuth";
import Link from "next/link";
import { motion } from "framer-motion";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, logout } = useAuth();

  const handleLogin = async (e: any) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = new URLSearchParams();
      data.append("username", email);
      data.append("password", password);
      
      const res = await api.post("/token", data);

      console.log("LOGIN RESPONSE:", res.data);

      await login(res.data.access_token);
     } catch (err: any) {
       setError(
         err.response?.data?.detail ||
         "Login failed. Check your credentials."
       );

  // Clear any old/stale authentication token.
  // This prevents an old valid session from making
  // an incorrect login appear successful.
      try {
        logout();
       }catch{
    // Ignore logout navigation errors here.
       }
     }
 finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-background relative overflow-hidden">
      {/* Decorative background circles */}
      <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-primary/20 rounded-full blur-3xl opacity-50"></div>
      <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-accent/20 rounded-full blur-3xl opacity-50"></div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md bg-secondary/50 backdrop-blur-xl p-8 rounded-2xl shadow-2xl border border-white/5 z-10"
      >
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2 text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent">Welcome Back</h1>
          <p className="text-gray-400">Sign in to your MindSense account.</p>
        </div>
        
        {error && <div className="bg-red-500/20 text-red-300 p-3 rounded-lg mb-6 text-sm text-center border border-red-500/30">{error}</div>}
        
        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Email</label>
            <input required type="email" onChange={(e) => setEmail(e.target.value)} className="w-full p-3 bg-background/50 border border-white/10 rounded-xl focus:outline-none focus:border-primary transition-colors text-white" placeholder="you@example.com" />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Password</label>
            <input required type="password" onChange={(e) => setPassword(e.target.value)} className="w-full p-3 bg-background/50 border border-white/10 rounded-xl focus:outline-none focus:border-primary transition-colors text-white" placeholder="••••••••" />
          </div>

          <button disabled={loading} type="submit" className="w-full bg-gradient-to-r from-primary to-accent py-3 rounded-xl font-medium text-white hover:opacity-90 transition-opacity">
            {loading ? "Logging in..." : "Log In"}
          </button>
        </form>
        
        <p className="text-center text-sm text-gray-400 mt-6">
          Don't have an account? <Link href="/signup" className="text-primary hover:underline">Sign Up</Link>
        </p>
      </motion.div>
    </div>
  );
}