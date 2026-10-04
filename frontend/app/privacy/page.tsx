import Link from "next/link";
import { Shield, Lock, Eye, Database, Bell, UserCheck, ArrowLeft } from "lucide-react";
import Footer from "../../components/Footer";

export const metadata = {
  title: "Privacy Policy",
  description: "MindSense AI Privacy Policy and Data Protection Practices",
};

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Header */}
      <header className="border-b border-white/10 bg-secondary/20 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
            <ArrowLeft size={16} /> Back to Home
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
              <span className="font-bold text-white text-xs">M</span>
            </div>
            <span className="font-bold text-white text-sm">MindSense AI</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto px-6 py-12 md:py-16">
        <div className="mb-10 text-center md:text-left">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold mb-4">
            <Shield size={13} /> Data Privacy & Transparency
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight mb-3">Privacy Policy</h1>
          <p className="text-gray-400 text-sm">Last Updated: September 2026</p>
        </div>

        {/* Highlights Banner */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-12">
          <div className="bg-secondary/40 border border-white/5 rounded-2xl p-5">
            <Lock className="text-primary mb-2" size={24} />
            <h4 className="font-semibold text-white text-sm mb-1">Zero Commercial Resale</h4>
            <p className="text-xs text-gray-400">We never sell, rent, or monetize your emotional reflections or personal chat history.</p>
          </div>
          <div className="bg-secondary/40 border border-white/5 rounded-2xl p-5">
            <Eye className="text-accent mb-2" size={24} />
            <h4 className="font-semibold text-white text-sm mb-1">PII-Masked Logs</h4>
            <p className="text-xs text-gray-400">All application logs mask contact numbers, credentials, and sensitive identifiers.</p>
          </div>
          <div className="bg-secondary/40 border border-white/5 rounded-2xl p-5">
            <UserCheck className="text-green-400 mb-2" size={24} />
            <h4 className="font-semibold text-white text-sm mb-1">User Control</h4>
            <p className="text-xs text-gray-400">You maintain full authority to inspect, export, or permanently delete your account data.</p>
          </div>
        </div>

        {/* Policy Sections */}
        <div className="space-y-8 text-sm leading-relaxed text-gray-300">
          <section className="bg-secondary/20 border border-white/5 rounded-2xl p-6 md:p-8">
            <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
              1. Our Privacy Philosophy
            </h2>
            <p>
              MindSense AI was founded on the fundamental principle that psychological wellness conversations require the highest echelon of privacy and ethical responsibility. Your thoughts, emotions, and interactions are private. We do not use your personal conversations to train public third-party foundation models without consent, nor do we disclose emotional data to advertisers, insurance providers, or commercial data brokers.
            </p>
          </section>

          <section className="bg-secondary/20 border border-white/5 rounded-2xl p-6 md:p-8">
            <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
              <Database size={18} className="text-primary" /> 2. Information We Collect
            </h2>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li>
                <strong className="text-white">Account Information:</strong> Full name, email address, password (stored using industry-standard salted cryptographic hashing), and personal phone number.
              </li>
              <li>
                <strong className="text-white">Emergency Contacts:</strong> Names and mobile phone numbers of up to two trusted contacts provided directly by you to receive automated emergency crisis SMS notifications.
              </li>
              <li>
                <strong className="text-white">Conversational & Multimodal Inputs:</strong> Text messages, real-time voice recordings, and optional facial video frames submitted during interactive sessions. Audio recordings and live camera frames are processed dynamically for transcription and emotional valence detection, and are not retained as permanent media files once analyzed.
              </li>
              <li>
                <strong className="text-white">Technical & Session Metadata:</strong> Session timestamps, ephemeral rate-limiting keys, and language preference headers.
              </li>
            </ul>
          </section>

          <section className="bg-secondary/20 border border-white/5 rounded-2xl p-6 md:p-8">
            <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
              3. How We Process and Use Information
            </h2>
            <p className="mb-2">Your information is used strictly to power the core functions of MindSense AI:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li>Providing empathetic, real-time conversational responses tailored to your emotional state.</li>
              <li>Detecting crisis escalations, acute distress, or self-harm indicators to activate safety protocols.</li>
              <li>Transmitting emergency SMS notifications strictly to your designated contacts when an escalated crisis is detected.</li>
              <li>Protecting platform integrity against denial-of-service, automated scraping, and credential stuffing.</li>
            </ul>
          </section>

          <section className="bg-secondary/20 border border-white/5 rounded-2xl p-6 md:p-8">
            <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
              <Lock size={18} className="text-accent" /> 4. Security & Cryptographic Controls
            </h2>
            <p className="mb-2">MindSense AI implements defense-in-depth security hardening:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong className="text-white">Transport Security:</strong> Strict Transport Security (HSTS) with TLS 1.3 enforced across all web and API communications.</li>
              <li><strong className="text-white">Authentication:</strong> JSON Web Tokens (JWT) using short-lived expiration windows, cryptographic signature verification, and automated token blacklisting upon logout.</li>
              <li><strong className="text-white">Isolation & Access Controls:</strong> All chat sessions, emergency contacts, and profile records are strictly partitioned and validated against authenticated user IDs. Cross-user access is blocked with 403 Forbidden.</li>
              <li><strong className="text-white">PII Sanitization:</strong> Server-side privacy validation regexes actively mask phone numbers and credentials before output to application logs.</li>
            </ul>
          </section>

          <section className="bg-secondary/20 border border-white/5 rounded-2xl p-6 md:p-8">
            <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
              <Bell size={18} className="text-pink-400" /> 5. Emergency SOS Dispatches
            </h2>
            <p>
              When our multi-turn safety state machine detects acute, persistent crisis or explicit self-harm intent, MindSense AI dispatches an automated SMS alert via trusted gateway partners (e.g., Fast2SMS or an Android SMS gateway). This dispatch contains only essential supportive alert text and does not include your full conversation transcript or private session history.
            </p>
          </section>

          <section className="bg-secondary/20 border border-white/5 rounded-2xl p-6 md:p-8">
            <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
              6. Your Privacy Rights & Data Deletion
            </h2>
            <p className="mb-2">
              Under applicable global privacy regulations (including GDPR, CCPA, and India's Digital Personal Data Protection Act), you hold the following rights:
            </p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong className="text-white">Right of Access:</strong> Review your account details and chat history at any time through your dashboard.</li>
              <li><strong className="text-white">Right of Rectification:</strong> Update or replace emergency contact information in real time via Profile Settings.</li>
              <li><strong className="text-white">Right of Erasure:</strong> Request permanent deletion of your account and associated session records.</li>
            </ul>
          </section>

          <section className="bg-secondary/20 border border-white/5 rounded-2xl p-6 md:p-8">
            <h2 className="text-lg font-bold text-white mb-3">7. Privacy Inquiries</h2>
            <p>
              If you have questions or concerns regarding our privacy controls, cryptographic implementations, or data practices, please contact our Data Protection Team at <span className="text-primary font-mono">privacy@mindsenseai.org</span>.
            </p>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}
