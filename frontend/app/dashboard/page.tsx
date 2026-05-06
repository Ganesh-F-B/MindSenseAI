"use client";
import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { useRouter } from "next/navigation";
import api from "../../lib/api";
import Link from "next/link";
import { motion } from "framer-motion";
import { Bell, AlertTriangle, MessageSquare, User as UserIcon, LogOut, Settings, ChevronRight } from "lucide-react";

export default function Dashboard() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [emergencyLoading, setEmergencyLoading] = useState(false);
  const [alertStatus, setAlertStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  const triggerEmergency = async () => {
    if (!confirm("Are you sure you want to trigger an emergency alert? This will contact your emergency contacts immediately.")) return;
    
    setEmergencyLoading(true);
    try {
      const res = await api.post("/emergency");
      setAlertStatus(res.data.message);
      setTimeout(() => setAlertStatus(null), 5000);
    } catch (err: any) {
      alert("Failed to send emergency alert.");
    } finally {
      setEmergencyLoading(false);
    }
  };

  if (loading || !user) {
    return <div className="min-h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-12 w-12 border-t-2 border-primary"></div></div>;
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside className="w-64 bg-secondary/30 border-r border-white/5 flex flex-col p-6 hidden md:flex">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <span className="font-bold text-white">M</span>
          </div>
          <span className="font-bold text-xl tracking-wide text-white">MindSense</span>
        </div>

        <nav className="flex-1 space-y-2">
          <Link href="/dashboard" className="flex items-center gap-3 px-4 py-3 rounded-xl bg-primary/20 text-primary transition-colors">
            <UserIcon size={20} /> Dashboard
          </Link>
          <Link href="/chat" className="flex items-center gap-3 px-4 py-3 rounded-xl text-gray-400 hover:bg-white/5 hover:text-white transition-colors">
            <MessageSquare size={20} /> AI Chat
          </Link>
          <Link href="/profile" className="flex items-center gap-3 px-4 py-3 rounded-xl text-gray-400 hover:bg-white/5 hover:text-white transition-colors">
            <UserIcon size={20} /> Profile
          </Link>
          <Link href="/settings" className="flex items-center gap-3 px-4 py-3 rounded-xl text-gray-400 hover:bg-white/5 hover:text-white transition-colors">
            <Settings size={20} /> Settings
          </Link>
        </nav>

        <button onClick={logout} className="flex items-center gap-3 px-4 py-3 rounded-xl text-gray-400 hover:bg-white/5 hover:text-red-400 transition-colors mt-auto">
          <LogOut size={20} /> Logout
        </button>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 md:p-12 overflow-y-auto">
        <header className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Hello, {user.full_name} 👋</h1>
            <p className="text-gray-400">Welcome to your mental health dashboard.</p>
          </div>
          <button className="p-3 rounded-full bg-secondary/50 border border-white/10 text-gray-300 hover:text-white transition-colors">
            <Bell size={20} />
          </button>
        </header>

        {alertStatus && (
          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-8 p-4 bg-green-500/20 border border-green-500/30 text-green-300 rounded-xl flex items-center gap-3">
            <Bell size={20} /> {alertStatus}
          </motion.div>
        )}

        {/* Emergency Card */}
        <div className="mb-8 bg-red-500/10 border border-red-500/20 rounded-2xl p-6 md:p-8 flex flex-col md:flex-row items-center justify-between gap-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3"></div>
          <div className="z-10 text-center md:text-left">
            <h2 className="text-2xl font-bold text-red-400 flex items-center justify-center md:justify-start gap-2 mb-2">
              <AlertTriangle size={24} /> Emergency Alert System
            </h2>
            <p className="text-red-300/80 max-w-lg">
              Pressing the emergency button will instantly notify your trusted contacts ({user.emergency_contacts.map(c => c.name).join(', ')}) with your current status.
            </p>
          </div>
          <button 
            onClick={triggerEmergency} 
            disabled={emergencyLoading}
            className="z-10 shrink-0 bg-red-600 hover:bg-red-500 text-white font-bold py-4 px-8 rounded-full shadow-lg shadow-red-600/30 transition-all hover:scale-105 flex items-center gap-2 animate-pulse"
          >
            <AlertTriangle size={20} />
            {emergencyLoading ? "Sending..." : "SOS / TRIGGER ALERT"}
          </button>
        </div>

        {/* Action Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link href="/chat">
            <div className="group bg-secondary/30 hover:bg-secondary/50 border border-white/5 hover:border-primary/30 p-8 rounded-2xl transition-all h-full flex flex-col justify-between cursor-pointer">
              <div>
                <div className="w-12 h-12 rounded-full bg-primary/20 text-primary flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <MessageSquare size={24} />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Talk to MindSense</h3>
                <p className="text-gray-400">Start a conversation to vent, seek guidance, or just have someone listen.</p>
              </div>
              <div className="mt-8 text-primary font-medium group-hover:translate-x-2 transition-transform inline-block">Start Session →</div>
            </div>
          </Link>
          
          <Link href="/profile" className="block group bg-secondary/30 hover:bg-secondary/50 border border-white/5 hover:border-accent/30 p-8 rounded-2xl h-full flex flex-col transition-all cursor-pointer">
            <div className="w-12 h-12 rounded-full bg-accent/20 text-accent flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <UserIcon size={24} />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Your Profile</h3>
            <div className="space-y-4 mt-4 flex-1">
              <div className="flex justify-between items-center border-b border-white/5 pb-3">
                <span className="text-gray-400">Email</span>
                <span className="text-white truncate max-w-[180px]">{user.email}</span>
              </div>
              <div className="flex justify-between items-center border-b border-white/5 pb-3">
                <span className="text-gray-400">Phone</span>
                <span className="text-white">{user.phone_number}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Contacts</span>
                <span className="text-white">{user.emergency_contacts.length} saved</span>
              </div>
            </div>
            <div className="mt-6 text-accent font-medium group-hover:translate-x-2 transition-transform inline-flex items-center gap-1">
              Manage Contacts <ChevronRight size={16}/>
            </div>
          </Link>
        </div>
      </main>
    </div>
  );
}