import Link from "next/link";
import { AlertCircle, Home, MessageSquare, LifeBuoy } from "lucide-react";

export const metadata = {
  title: "Page Not Found",
  description: "The requested page could not be found.",
};

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Decorative gradient blur */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="relative z-10 max-w-md w-full text-center bg-secondary/30 backdrop-blur-xl border border-white/10 rounded-3xl p-8 sm:p-10 shadow-2xl">
        <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-6">
          <AlertCircle className="text-yellow-400" size={32} />
        </div>

        <span className="text-xs font-mono font-semibold uppercase tracking-widest text-primary mb-2 block">
          404 — Not Found
        </span>

        <h1 className="text-2xl sm:text-3xl font-bold text-white mb-3">
          Page Not Located
        </h1>

        <p className="text-sm text-gray-400 mb-8 leading-relaxed">
          The requested page could not be found or may have been moved. If you are experiencing distress, support is always available.
        </p>

        <div className="space-y-3">
          <Link
            href="/"
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-white/10 hover:bg-white/15 text-white text-sm font-medium transition-colors border border-white/5"
          >
            <Home size={16} /> Return to Home
          </Link>
          <Link
            href="/chat"
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-primary to-accent text-white text-sm font-medium hover:opacity-90 transition-opacity shadow-lg shadow-primary/20"
          >
            <MessageSquare size={16} /> Go to AI Companion
          </Link>
          <Link
            href="/safety"
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs text-pink-400 hover:text-pink-300 hover:bg-pink-500/10 transition-colors"
          >
            <LifeBuoy size={14} /> Immediate Crisis Helplines
          </Link>
        </div>
      </div>

      <div className="mt-8 text-xs text-gray-500 relative z-10">
        MindSense AI • Compassionate, secure, and confidential
      </div>
    </div>
  );
}
