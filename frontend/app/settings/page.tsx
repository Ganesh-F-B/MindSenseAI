"use client";
import { useAuth } from "../../hooks/useAuth";
import Link from "next/link";
import api from "../../lib/api";
import { useState, useEffect } from "react";
import {
  LogOut, Trash2, Settings as SettingsIcon, Moon, Sun, Globe,
  Bell, BellOff, LayoutDashboard, MessageSquare, User, ChevronRight,
  AlertTriangle, X, ShieldAlert
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function SettingsPage() {
  const { user, logout } = useAuth();

  // Load saved preferences from localStorage
  const [darkMode, setDarkMode]           = useState(true);
  const [notifications, setNotifications] = useState(false);
  const [appLanguage, setAppLanguage]     = useState("English");

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteInput, setDeleteInput]             = useState("");
  const [deleting, setDeleting]                   = useState(false);
  const [deleteError, setDeleteError]             = useState("");
  const [notifStatus, setNotifStatus]             = useState("");

  // Load saved preferences on mount
  useEffect(() => {
    const savedDark = localStorage.getItem("ms_darkmode");
    const savedLang = localStorage.getItem("ms_language");
    const savedNotif = localStorage.getItem("ms_notifications");
    if (savedDark !== null) {
      const isDark = savedDark === "true";
      setDarkMode(isDark);
      if (!isDark) {
        document.documentElement.classList.add("light");
      } else {
        document.documentElement.classList.remove("light");
      }
    }
    if (savedLang) setAppLanguage(savedLang);
    if (savedNotif !== null) setNotifications(savedNotif === "true");
  }, []);


  const toggleDarkMode = () => {
    const next = !darkMode;
    setDarkMode(next);
    localStorage.setItem("ms_darkmode", String(next));
    if (next) {
      // Dark mode ON → remove light class
      document.documentElement.classList.remove("light");
    } else {
      // Light mode ON → add light class
      document.documentElement.classList.add("light");
    }
  };


  const changeLanguage = (lang: string) => {
    setAppLanguage(lang);
    localStorage.setItem("ms_language", lang);
  };

  const toggleNotifications = async () => {
    if (!notifications) {
      if (!("Notification" in window)) {
        setNotifStatus("Your browser doesn't support notifications.");
        return;
      }
      const permission = await Notification.requestPermission();
      if (permission === "granted") {
        setNotifications(true);
        localStorage.setItem("ms_notifications", "true");
        setNotifStatus("✅ Notifications enabled!");
        new Notification("MindSense AI", { body: "Emergency alerts are now enabled on this device." });
      } else {
        setNotifStatus("❌ Permission denied. Enable in browser settings.");
      }
    } else {
      setNotifications(false);
      localStorage.setItem("ms_notifications", "false");
      setNotifStatus("Notifications disabled.");
    }
    setTimeout(() => setNotifStatus(""), 3000);
  };

  const handleDeleteAccount = async () => {
    if (deleteInput !== "DELETE") {
      setDeleteError("Please type DELETE exactly to confirm.");
      return;
    }
    setDeleting(true);
    setDeleteError("");
    try {
      await api.delete("/users/me");
      logout();
    } catch (err: any) {
      setDeleteError(err?.response?.data?.detail || "Failed to delete account. Try again.");
      setDeleting(false);
    }
  };

  const Toggle = ({ value, onChange }: { value: boolean; onChange: () => void }) => (
    <button
      onClick={onChange}
      className={`relative w-12 h-6 rounded-full transition-colors duration-300 focus:outline-none ${value ? "bg-blue-600" : "bg-gray-600"}`}
    >
      <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-300 ${value ? "translate-x-6" : "translate-x-0"}`} />
    </button>
  );

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex text-white">
      {/* Sidebar */}
      <aside className="w-64 bg-[#1e293b] border-r border-white/5 flex-col p-6 hidden md:flex">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center shadow-lg">
            <span className="font-bold text-white text-lg font-serif">M</span>
          </div>
          <span className="font-bold text-xl tracking-wide text-white">MindSense</span>
        </div>
        <nav className="flex-1 space-y-1">
          {[
            { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
            { href: "/chat",      icon: MessageSquare,   label: "AI Chat"   },
            { href: "/profile",   icon: User,            label: "Profile"   },
            { href: "/settings",  icon: SettingsIcon,    label: "Settings", active: true },
          ].map(({ href, icon: Icon, label, active }) => (
            <Link key={href} href={href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors text-sm font-medium
                ${active ? "bg-blue-600/20 text-blue-400" : "text-gray-400 hover:bg-white/5 hover:text-white"}`}>
              <Icon size={17} /> {label}
            </Link>
          ))}
        </nav>
        <div className="pt-4 border-t border-white/10">
          <div className="flex items-center gap-3 px-2">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-sm font-bold">
              {user?.full_name?.[0]?.toUpperCase() ?? "U"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.full_name}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 p-6 md:p-12 overflow-y-auto">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 flex items-center justify-center">
              <SettingsIcon size={20} className="text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Settings</h1>
              <p className="text-sm text-gray-500">Manage your account preferences</p>
            </div>
          </div>

          <div className="space-y-5">

            {/* Account Preferences */}
            <div className="bg-[#1e293b] border border-white/10 rounded-3xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/5">
                <h2 className="text-base font-semibold text-white">Account Preferences</h2>
              </div>
              <div className="divide-y divide-white/5">

                {/* Dark Mode */}
                <div className="flex items-center justify-between px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-slate-700/50 flex items-center justify-center">
                      {darkMode ? <Moon size={16} className="text-blue-300" /> : <Sun size={16} className="text-yellow-300" />}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">Dark Mode</p>
                      <p className="text-xs text-gray-500">{darkMode ? "Currently dark theme" : "Currently light theme"}</p>
                    </div>
                  </div>
                  <Toggle value={darkMode} onChange={toggleDarkMode} />
                </div>

                {/* Language */}
                <div className="flex items-center justify-between px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-slate-700/50 flex items-center justify-center">
                      <Globe size={16} className="text-green-300" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">App Language</p>
                      <p className="text-xs text-gray-500">Saved: {appLanguage}</p>
                    </div>
                  </div>
                  <select
                    value={appLanguage}
                    onChange={e => changeLanguage(e.target.value)}
                    className="bg-[#0f172a] border border-white/10 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500/50 cursor-pointer"
                  >
                    {["English","Hindi","Kannada","Tamil","Telugu","Malayalam","Bengali","Gujarati","Marathi","Punjabi","Urdu"].map(l =>
                      <option key={l} value={l}>{l}</option>
                    )}
                  </select>
                </div>

                {/* Notifications */}
                <div className="flex items-center justify-between px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-slate-700/50 flex items-center justify-center">
                      {notifications ? <Bell size={16} className="text-yellow-300" /> : <BellOff size={16} className="text-gray-400" />}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">Browser Notifications</p>
                      <p className="text-xs text-gray-500">
                        {notifStatus || (notifications ? "Emergency alerts enabled on this browser" : "Enable to get emergency alerts")}
                      </p>
                    </div>
                  </div>
                  <Toggle value={notifications} onChange={toggleNotifications} />
                </div>
              </div>
            </div>

            {/* Account Info */}
            <div className="bg-[#1e293b] border border-white/10 rounded-3xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/5">
                <h2 className="text-base font-semibold text-white">Account Info</h2>
              </div>
              <div className="px-6 py-4 flex items-center gap-4">
                <div className="w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xl font-bold flex-shrink-0">
                  {user?.full_name?.[0]?.toUpperCase() ?? "U"}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-white">{user?.full_name}</p>
                  <p className="text-sm text-gray-400">{user?.email}</p>
                  <p className="text-xs text-gray-600 mt-1">{user?.phone_number}</p>
                </div>
                <Link href="/profile"
                  className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors">
                  Edit <ChevronRight size={14} />
                </Link>
              </div>
            </div>

            {/* Danger Zone */}
            <div className="bg-red-500/5 border border-red-500/20 rounded-3xl overflow-hidden">
              <div className="px-6 py-4 border-b border-red-500/10 flex items-center gap-2">
                <ShieldAlert size={17} className="text-red-400" />
                <h2 className="text-base font-semibold text-red-400">Danger Zone</h2>
              </div>
              <div className="p-6 space-y-4">

                {/* Logout */}
                <div className="flex items-center justify-between p-4 bg-black/20 rounded-2xl border border-white/5">
                  <div>
                    <p className="text-sm font-medium text-white">Log Out</p>
                    <p className="text-xs text-gray-500 mt-0.5">Sign out from this device</p>
                  </div>
                  <button onClick={logout}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-xl transition-colors font-medium">
                    <LogOut size={15} /> Log Out
                  </button>
                </div>

                {/* Delete Account */}
                <div className="flex items-center justify-between p-4 bg-red-500/10 rounded-2xl border border-red-500/20">
                  <div>
                    <p className="text-sm font-medium text-red-300">Delete Account</p>
                    <p className="text-xs text-red-400/60 mt-0.5">Permanently removes all data. Cannot be undone.</p>
                  </div>
                  <button onClick={() => setShowDeleteConfirm(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm rounded-xl transition-colors font-medium">
                    <Trash2 size={15} /> Delete
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {showDeleteConfirm && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="bg-[#1e293b] border border-red-500/30 rounded-3xl p-8 max-w-md w-full shadow-2xl">

              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-2xl bg-red-500/20 flex items-center justify-center">
                  <AlertTriangle size={24} className="text-red-400" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Delete Account</h3>
                  <p className="text-sm text-red-400">This cannot be undone</p>
                </div>
              </div>

              <p className="text-gray-400 text-sm mb-6 leading-relaxed">
                This will permanently delete your account, all chat history, emergency contacts, and all associated data.
                <strong className="text-white"> This action is irreversible.</strong>
              </p>

              <div className="mb-5">
                <label className="text-xs text-gray-500 mb-2 block">
                  Type <span className="text-red-400 font-bold font-mono">DELETE</span> to confirm
                </label>
                <input
                  value={deleteInput}
                  onChange={e => setDeleteInput(e.target.value)}
                  placeholder="Type DELETE here"
                  className="w-full bg-black/30 border border-red-500/30 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-red-500 transition-colors font-mono"
                />
                {deleteError && (
                  <p className="text-red-400 text-xs mt-2">{deleteError}</p>
                )}
              </div>

              <div className="flex gap-3">
                <button onClick={() => { setShowDeleteConfirm(false); setDeleteInput(""); setDeleteError(""); }}
                  className="flex-1 py-3 rounded-xl border border-white/10 text-gray-400 hover:text-white hover:bg-white/5 transition-colors text-sm font-medium flex items-center justify-center gap-2">
                  <X size={15} /> Cancel
                </button>
                <button onClick={handleDeleteAccount} disabled={deleting || deleteInput !== "DELETE"}
                  className="flex-1 py-3 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors flex items-center justify-center gap-2">
                  {deleting
                    ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    : <><Trash2 size={15} /> Delete Forever</>}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}