"use client";

import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="flex justify-between items-center p-5 border-b border-white/10">
      <h1 className="text-xl font-bold text-indigo-400">MindSense AI</h1>

      <div className="flex gap-4">
        <Link href="/chat">Chat</Link>
        <Link href="/dashboard">Dashboard</Link>
        <Link href="/login">Login</Link>
      </div>
    </nav>
  );
}