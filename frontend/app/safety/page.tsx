import Link from "next/link";
import { HeartHandshake, PhoneCall, ShieldCheck, LifeBuoy, Sparkles, AlertCircle, ArrowLeft } from "lucide-react";
import Footer from "../../components/Footer";

export const metadata = {
  title: "Safety & Crisis Resources",
  description: "MindSense AI Crisis Support, Emergency Helplines, and Safety Architecture",
};

export default function SafetyResources() {
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
      <main className="flex-1 max-w-5xl mx-auto px-6 py-12 md:py-16">
        <div className="mb-10 text-center md:text-left">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-pink-500/10 border border-pink-500/20 text-pink-400 text-xs font-semibold mb-4">
            <LifeBuoy size={13} /> Immediate Help & Crisis Safety
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight mb-3">
            Crisis Support & Safety Architecture
          </h1>
          <p className="text-gray-400 text-sm max-w-2xl leading-relaxed">
            If you are going through a difficult time, you are not alone. Free, confidential, and empathetic support is available 24 hours a day, 7 days a week.
          </p>
        </div>

        {/* Immediate Helpline Grid */}
        <div className="mb-12">
          <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <PhoneCall className="text-primary" size={20} /> 24/7 Verified Crisis Lifelines
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* India Section */}
            <div className="bg-secondary/40 border border-white/10 rounded-2xl p-6 hover:border-primary/40 transition-colors">
              <div className="flex items-center justify-between mb-4">
                <span className="px-2.5 py-1 rounded-md bg-blue-500/10 text-blue-400 text-xs font-semibold">India</span>
                <span className="text-xs text-green-400 font-medium">Available 24/7 • Free</span>
              </div>
              <h3 className="text-lg font-bold text-white mb-1">Tele-MANAS</h3>
              <p className="text-xs text-gray-400 mb-4">
                Ministry of Health & Family Welfare, Government of India. Multilingual mental health counseling.
              </p>
              <div className="space-y-2">
                <a
                  href="tel:14416"
                  className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-primary/20 border border-white/5 transition-colors text-white font-mono text-sm"
                >
                  <span>Short Code: <strong>14416</strong></span>
                  <span className="text-xs text-primary font-sans font-medium">Call Now →</span>
                </a>
                <a
                  href="tel:18008914416"
                  className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-primary/20 border border-white/5 transition-colors text-white font-mono text-sm"
                >
                  <span>Toll-Free: <strong>1800 891 4416</strong></span>
                  <span className="text-xs text-primary font-sans font-medium">Call Now →</span>
                </a>
              </div>
              <div className="mt-4 pt-4 border-t border-white/5 text-xs text-gray-400 space-y-1">
                <div><strong>Vandrevala Foundation:</strong> +91 9999 666 555 (24x7)</div>
                <div><strong>KIRAN Helpline:</strong> 1800-599-0019 (24x7)</div>
                <div><strong>National Emergency:</strong> 112</div>
              </div>
            </div>

            {/* United States & Canada */}
            <div className="bg-secondary/40 border border-white/10 rounded-2xl p-6 hover:border-primary/40 transition-colors">
              <div className="flex items-center justify-between mb-4">
                <span className="px-2.5 py-1 rounded-md bg-purple-500/10 text-purple-400 text-xs font-semibold">USA & Canada</span>
                <span className="text-xs text-green-400 font-medium">Available 24/7 • Free</span>
              </div>
              <h3 className="text-lg font-bold text-white mb-1">988 Suicide & Crisis Lifeline</h3>
              <p className="text-xs text-gray-400 mb-4">
                Immediate, confidential support for anyone in distress or crisis across the US and Canada.
              </p>
              <div className="space-y-2">
                <a
                  href="tel:988"
                  className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-accent/20 border border-white/5 transition-colors text-white font-mono text-sm"
                >
                  <span>Call or Text: <strong>988</strong></span>
                  <span className="text-xs text-accent font-sans font-medium">Call 988 →</span>
                </a>
                <a
                  href="sms:741741?body=HOME"
                  className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-accent/20 border border-white/5 transition-colors text-white font-mono text-sm"
                >
                  <span>Crisis Text Line: <strong>Text HOME to 741741</strong></span>
                  <span className="text-xs text-accent font-sans font-medium">Text Now →</span>
                </a>
              </div>
              <div className="mt-4 pt-4 border-t border-white/5 text-xs text-gray-400 space-y-1">
                <div><strong>The Trevor Project (LGBTQ+):</strong> 1-866-488-7386</div>
                <div><strong>Veterans Crisis Line:</strong> Dial 988, then press 1</div>
              </div>
            </div>

            {/* United Kingdom */}
            <div className="bg-secondary/40 border border-white/10 rounded-2xl p-6 hover:border-primary/40 transition-colors">
              <div className="flex items-center justify-between mb-4">
                <span className="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 text-xs font-semibold">United Kingdom</span>
                <span className="text-xs text-green-400 font-medium">Available 24/7 • Free</span>
              </div>
              <h3 className="text-lg font-bold text-white mb-1">NHS & Samaritans</h3>
              <p className="text-xs text-gray-400 mb-4">
                Round-the-clock urgent mental health support and confidential emotional listening.
              </p>
              <div className="space-y-2">
                <a
                  href="tel:111"
                  className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-emerald-500/20 border border-white/5 transition-colors text-white font-mono text-sm"
                >
                  <span>NHS Mental Health: <strong>111</strong></span>
                  <span className="text-xs text-emerald-400 font-sans font-medium">Call 111 →</span>
                </a>
                <a
                  href="tel:116123"
                  className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-emerald-500/20 border border-white/5 transition-colors text-white font-mono text-sm"
                >
                  <span>Samaritans: <strong>116 123</strong></span>
                  <span className="text-xs text-emerald-400 font-sans font-medium">Call 116 123 →</span>
                </a>
              </div>
            </div>

            {/* International */}
            <div className="bg-secondary/40 border border-white/10 rounded-2xl p-6 hover:border-primary/40 transition-colors">
              <div className="flex items-center justify-between mb-4">
                <span className="px-2.5 py-1 rounded-md bg-yellow-500/10 text-yellow-400 text-xs font-semibold">Worldwide</span>
                <span className="text-xs text-green-400 font-medium">130+ Countries</span>
              </div>
              <h3 className="text-lg font-bold text-white mb-1">Find A Helpline</h3>
              <p className="text-xs text-gray-400 mb-4">
                Global directory of free, confidential support lines in over 130 countries and multiple languages.
              </p>
              <div className="space-y-2">
                <a
                  href="https://findahelpline.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-yellow-500/20 border border-white/5 transition-colors text-white text-sm"
                >
                  <span>Browse Directory: <strong>findahelpline.com</strong></span>
                  <span className="text-xs text-yellow-400 font-medium">Visit Website ↗</span>
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* MindSense Safety Architecture Explanation */}
        <section className="bg-secondary/20 border border-white/5 rounded-2xl p-6 md:p-8 mb-10">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <ShieldCheck size={22} className="text-primary" /> How MindSense AI Protects You
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
            <div className="space-y-2">
              <h4 className="font-semibold text-white flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs font-bold">1</span>
                Assessment First
              </h4>
              <p className="text-xs text-gray-400 leading-relaxed">
                When crisis statements are first expressed, our AI initiates supportive safety containment and asks gently about your immediate well-being, avoiding premature alarm dispatch.
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold text-white flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-accent/20 text-accent flex items-center justify-center text-xs font-bold">2</span>
                Automated SOS Escalation
              </h4>
              <p className="text-xs text-gray-400 leading-relaxed">
                If acute distress persists or explicit imminent self-harm intent is expressed, the system immediately escalates and dispatches urgent SMS notifications to your emergency contacts.
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold text-white flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-pink-500/20 text-pink-400 flex items-center justify-center text-xs font-bold">3</span>
                Strict Contact Ownership
              </h4>
              <p className="text-xs text-gray-400 leading-relaxed">
                Emergency alerts are dispatched strictly and exclusively to your verified contacts. Cryptographic authorization boundaries guarantee complete isolation across user accounts.
              </p>
            </div>
          </div>
        </section>

        {/* Immediate Calming / Grounding Exercises */}
        <section className="bg-gradient-to-r from-primary/10 via-accent/10 to-transparent border border-white/10 rounded-2xl p-6 md:p-8 mb-10">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Sparkles size={20} className="text-accent" /> Grounding Techniques You Can Use Right Now
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
            <div className="bg-background/40 p-5 rounded-xl border border-white/5">
              <h4 className="font-semibold text-white mb-2">Box Breathing (4-4-4-4)</h4>
              <ol className="list-decimal pl-5 space-y-1 text-xs text-gray-300">
                <li>Inhale slowly through your nose for 4 seconds.</li>
                <li>Hold your breath gently for 4 seconds.</li>
                <li>Exhale smoothly through your mouth for 4 seconds.</li>
                <li>Wait in calm stillness for 4 seconds. Repeat 4 times.</li>
              </ol>
            </div>
            <div className="bg-background/40 p-5 rounded-xl border border-white/5">
              <h4 className="font-semibold text-white mb-2">5-4-3-2-1 Sensory Grounding</h4>
              <ul className="space-y-1 text-xs text-gray-300">
                <li>👁️ <strong>5 things</strong> you can see around you</li>
                <li>✋ <strong>4 things</strong> you can physically feel or touch</li>
                <li>👂 <strong>3 things</strong> you can hear right now</li>
                <li>👃 <strong>2 things</strong> you can smell</li>
                <li>👅 <strong>1 thing</strong> you can taste</li>
              </ul>
            </div>
          </div>
        </section>

        {/* Back Link */}
        <div className="text-center pt-4">
          <Link
            href="/chat"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-full bg-gradient-to-r from-primary to-accent text-white font-medium hover:opacity-90 transition-opacity shadow-lg"
          >
            <HeartHandshake size={18} /> Return to AI Companion Chat
          </Link>
        </div>
      </main>

      <Footer />
    </div>
  );
}
