"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { Heart, Shield, Globe, Mic } from "lucide-react";
import Footer from "../components/Footer";

export default function Home() {
  return (
    <div className="min-h-screen bg-background overflow-hidden selection:bg-primary/30">
      {/* Background Gradients */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-primary/20 rounded-full blur-[120px]"></div>
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-accent/20 rounded-full blur-[120px]"></div>
      </div>

      {/* Navbar */}
      <nav className="relative z-10 max-w-7xl mx-auto px-6 py-6 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg shadow-primary/20">
            <span className="font-bold text-white text-lg">M</span>
          </div>
          <span className="font-bold text-xl tracking-wide text-white">MindSense</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login" className="text-gray-300 hover:text-white transition-colors font-medium px-4 py-2">Log In</Link>
          <Link href="/signup" className="bg-white text-background hover:bg-gray-100 transition-colors font-medium px-6 py-2.5 rounded-full shadow-lg">Get Started</Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 pt-20 pb-32 text-center">
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="max-w-4xl mx-auto"
        >
          <h1 className="text-5xl md:text-7xl font-extrabold text-white tracking-tight mb-8 leading-tight">
            Your Empathetic <br className="hidden md:block"/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-accent to-purple-400">
              AI Mental Health Companion
            </span>
          </h1>
          <p className="text-lg md:text-xl text-gray-400 mb-12 max-w-2xl mx-auto leading-relaxed">
            Experience a safe, judgment-free space to talk, reflect, and find support. Available 24/7 in multiple languages, with emergency assistance when you need it most.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/signup" className="w-full sm:w-auto bg-gradient-to-r from-primary to-accent text-white hover:opacity-90 transition-opacity font-bold px-8 py-4 rounded-full shadow-xl shadow-primary/20 flex items-center justify-center gap-2">
              Start Your Journey
            </Link>
            <Link href="/login" className="w-full sm:w-auto bg-secondary/50 backdrop-blur border border-white/10 hover:bg-secondary transition-colors text-white font-bold px-8 py-4 rounded-full flex items-center justify-center">
              Sign In
            </Link>
          </div>
        </motion.div>

        {/* Features Grid */}
        <motion.div 
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-32 text-left"
        >
          {[
            { icon: <Heart className="text-pink-400" size={32}/>, title: "Empathetic AI", desc: "Advanced LLM trained to provide warm, supportive, and understanding responses." },
            { icon: <Globe className="text-blue-400" size={32}/>, title: "Multilingual", desc: "Speak and chat in over 10 Indian languages seamlessly." },
            { icon: <Shield className="text-green-400" size={32}/>, title: "Emergency SOS", desc: "Instantly alert your trusted contacts if you are in distress." },
            { icon: <Mic className="text-accent" size={32}/>, title: "Voice & Video", desc: "Express yourself naturally with continuous voice recording and video input." }
          ].map((feat, idx) => (
            <div key={idx} className="bg-secondary/40 backdrop-blur border border-white/5 p-8 rounded-3xl hover:bg-secondary/60 transition-colors">
              <div className="w-14 h-14 rounded-2xl bg-white/5 flex items-center justify-center mb-6">
                {feat.icon}
              </div>
              <h3 className="text-xl font-bold text-white mb-3">{feat.title}</h3>
              <p className="text-gray-400 leading-relaxed">{feat.desc}</p>
            </div>
          ))}
        </motion.div>
      </main>

      <Footer />
    </div>
  );
}