import Link from "next/link";
import { Shield, Heart, AlertTriangle } from "lucide-react";

export default function Footer() {
  return (
    <footer className="relative z-10 border-t border-white/10 bg-secondary/30 backdrop-blur-md text-gray-400 py-12 px-6">
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
        {/* Brand Column */}
        <div className="md:col-span-2 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-md shadow-primary/20">
              <span className="font-bold text-white text-sm">M</span>
            </div>
            <span className="font-bold text-lg tracking-wide text-white">MindSense AI</span>
          </div>
          <p className="text-sm text-gray-400 max-w-md leading-relaxed">
            Your empathetic, 24/7 AI mental wellness companion. Providing a safe, reflective, and judgment-free space with real-time emotion support and emergency safety assistance.
          </p>
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1.5"><Shield size={14} className="text-primary" /> End-to-End Encrypted</span>
            <span className="flex items-center gap-1.5"><Heart size={14} className="text-pink-400" /> Crisis SOS Protected</span>
          </div>
        </div>

        {/* Quick Links */}
        <div>
          <h4 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">Platform</h4>
          <ul className="space-y-2.5 text-sm">
            <li>
              <Link href="/" className="hover:text-white transition-colors">Home</Link>
            </li>
            <li>
              <Link href="/chat" className="hover:text-white transition-colors">AI Chat</Link>
            </li>
            <li>
              <Link href="/dashboard" className="hover:text-white transition-colors">Wellness Dashboard</Link>
            </li>
            <li>
              <Link href="/login" className="hover:text-white transition-colors">Sign In</Link>
            </li>
          </ul>
        </div>

        {/* Legal & Safety */}
        <div>
          <h4 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">Safety & Legal</h4>
          <ul className="space-y-2.5 text-sm">
            <li>
              <Link href="/safety" className="hover:text-white transition-colors text-pink-400 font-medium">Crisis Resources & Helplines</Link>
            </li>
            <li>
              <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
            </li>
            <li>
              <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
            </li>
          </ul>
        </div>
      </div>

      {/* Critical Medical Disclaimer Banner */}
      <div className="max-w-7xl mx-auto border-t border-white/5 pt-6 pb-4">
        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 flex items-start gap-3 text-xs leading-relaxed text-yellow-200/90">
          <AlertTriangle size={18} className="text-yellow-400 shrink-0 mt-0.5" />
          <div>
            <strong className="font-semibold text-yellow-300">Important Medical & Crisis Notice: </strong>
            MindSenseAI is an artificial intelligence-powered supportive wellness companion and is <em>not</em> a licensed healthcare provider, medical clinic, psychiatrist, or suicide prevention hotline. MindSenseAI does not provide medical diagnosis, clinical treatment, or prescriptions. If you or someone you know is in immediate distress or experiencing suicidal thoughts, please call <strong>988</strong> (US/Canada), <strong>112</strong> (EU/India), or <strong>Tele-MANAS at 14416 / 1800-891-4416</strong> (India) immediately.
          </div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center text-xs text-gray-500 pt-4">
        <p>© 2026 MindSense AI. All rights reserved.</p>
        <p className="mt-2 sm:mt-0">Designed with safety, privacy, and compassion.</p>
      </div>
    </footer>
  );
}
