"use client";
import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { useRouter } from "next/navigation";
import api from "../../lib/api";
import Link from "next/link";
import { motion } from "framer-motion";
import { Bell, AlertTriangle, MessageSquare, User as UserIcon, LogOut, Settings, ChevronRight, Brain, TrendingUp, ShieldAlert, Activity } from "lucide-react";

// ── NLP Analytics types ────────────────────────────────────────────────────
interface NlpAnalytics {
  total_analyzed: number;
  counts: { Normal: number; Anxiety: number; Depression: number; Suicidal: number };
  avg_confidence: number;
}

const NLP_STATS = [
  { key: "Normal",     label: "Normal",     color: "text-green-400",  bg: "bg-green-500/10",  border: "border-green-500/20",  bar: "bg-green-500"  },
  { key: "Anxiety",    label: "Anxiety",    color: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/20", bar: "bg-yellow-500" },
  { key: "Depression", label: "Depression", color: "text-blue-400",   bg: "bg-blue-500/10",   border: "border-blue-500/20",   bar: "bg-blue-500"   },
  { key: "Suicidal",   label: "Suicidal",   color: "text-red-400",    bg: "bg-red-500/10",    border: "border-red-500/20",    bar: "bg-red-500"    },
] as const;

export default function Dashboard() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [emergencyLoading, setEmergencyLoading] = useState(false);
  const [alertStatus, setAlertStatus] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<NlpAnalytics | null>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (!user) return;
    api.get("/nlp-analytics")
      .then(res => setAnalytics(res.data))
      .catch(() => {}); // analytics are non-critical; fail silently
  }, [user]);

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

        {/* ── NLP Analytics Section ───────────────────────────────────── */}
        {analytics && (
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="mt-10"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 rounded-lg bg-primary/20 text-primary flex items-center justify-center">
                <Brain size={18} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Mental State Analytics</h2>
                <p className="text-xs text-gray-500">Based on your chat history — powered by NLP model</p>
              </div>
            </div>

            {/* Top summary row */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
              {/* Total messages */}
              <div className="bg-secondary/30 border border-white/5 rounded-2xl p-5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-primary/20 text-primary flex items-center justify-center flex-shrink-0">
                  <Activity size={20} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{analytics.total_analyzed}</p>
                  <p className="text-xs text-gray-400">Messages Analyzed</p>
                </div>
              </div>

              {/* Avg confidence */}
              <div className="bg-secondary/30 border border-white/5 rounded-2xl p-5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-accent/20 text-accent flex items-center justify-center flex-shrink-0">
                  <TrendingUp size={20} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{analytics.avg_confidence}%</p>
                  <p className="text-xs text-gray-400">Avg Confidence</p>
                </div>
              </div>

              {/* High-risk count */}
              <div className="col-span-2 md:col-span-1 bg-red-500/10 border border-red-500/20 rounded-2xl p-5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center flex-shrink-0">
                  <ShieldAlert size={20} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-red-400">{analytics.counts.Suicidal}</p>
                  <p className="text-xs text-red-300/70">High-Risk Messages</p>
                </div>
              </div>
            </div>

            {/* Per-state breakdown bars */}
            <div className="bg-secondary/30 border border-white/5 rounded-2xl p-6 space-y-4">
              <p className="text-sm font-semibold text-gray-300 mb-2">State Breakdown</p>
              {NLP_STATS.map(({ key, label, color, bg, border, bar }) => {
                const count = analytics.counts[key];
                const pct = analytics.total_analyzed > 0
                  ? Math.round((count / analytics.total_analyzed) * 100)
                  : 0;
                return (
                  <div key={key}>
                    <div className="flex justify-between items-center mb-1.5">
                      <span className={`text-sm font-medium ${color}`}>{label}</span>
                      <span className="text-sm text-gray-400">
                        <span className="text-white font-semibold">{count}</span>
                        {" "}<span className="text-gray-500">({pct}%)</span>
                      </span>
                    </div>
                    <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                        className={`h-full rounded-full ${bar}`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.section>
        )}
      </main>
    </div>
  );
}