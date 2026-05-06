"use client";

import Link from "next/link";

export default function Sidebar() {
  return (
    <div className="w-64 h-screen bg-white/5 border-r border-white/10 p-5">
      <h2 className="text-lg font-semibold mb-6">Menu</h2>

      <div className="flex flex-col gap-4">
        <Link href="/dashboard" className="text-white/70 hover:text-white transition-colors px-3 py-2 rounded hover:bg-white/10">Dashboard</Link>
        <Link href="/chat" className="text-white/70 hover:text-white transition-colors px-3 py-2 rounded hover:bg-white/10">Chat</Link>
        <Link href="/analytics" className="text-white/70 hover:text-white transition-colors px-3 py-2 rounded hover:bg-white/10">Analytics</Link>
        <Link href="/profile" className="text-white/70 hover:text-white transition-colors px-3 py-2 rounded hover:bg-white/10">Profile</Link>
      </div>
    </div>
  );
}