"use client";
import { useState } from "react";
import api from "../../lib/api";
import { useAuth } from "../../hooks/useAuth";
import Link from "next/link";
import { motion } from "framer-motion";

export default function Signup() {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    full_name: "",
    phone_number: "",
    contact1_name: "",
    contact1_phone: "",
    contact2_name: "",
    contact2_phone: ""
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleChange = (e: any) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSignup = async (e: any) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const payload = {
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        phone_number: formData.phone_number,
        emergency_contacts: [
          { name: formData.contact1_name, phone_number: formData.contact1_phone },
          { name: formData.contact2_name, phone_number: formData.contact2_phone }
        ]
      };
      
      await api.post("/signup", payload);
      
      // Auto-login
      const loginData = new URLSearchParams();
      loginData.append("username", formData.email);
      loginData.append("password", formData.password);
      
      const loginRes = await api.post("/token", loginData);
      await login(loginRes.data.access_token);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        const msgs = detail.map((d: any) => (typeof d === "string" ? d : d.msg || JSON.stringify(d))).join(", ");
        setError(msgs || "Signup failed");
      } else if (typeof detail === "string") {
        setError(detail);
      } else if (detail && typeof detail === "object") {
        setError(detail.message || JSON.stringify(detail));
      } else {
        setError("Signup failed");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-background relative overflow-hidden">
      {/* Decorative background circles */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 rounded-full blur-3xl opacity-50"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-accent/20 rounded-full blur-3xl opacity-50"></div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-2xl bg-secondary/50 backdrop-blur-xl p-8 rounded-2xl shadow-2xl border border-white/5 z-10"
      >
        <h1 className="text-3xl font-bold mb-2 text-center text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent">Join MindSense AI</h1>
        <p className="text-center text-gray-400 mb-8">Your empathetic mental health companion.</p>
        
        {error && <div className="bg-red-500/20 text-red-300 p-3 rounded-lg mb-6 text-sm text-center border border-red-500/30">{error}</div>}
        
        <form onSubmit={handleSignup} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Full Name</label>
              <input required name="full_name" onChange={handleChange} className="w-full p-3 bg-background/50 border border-white/10 rounded-xl focus:outline-none focus:border-primary transition-colors text-white" placeholder="John Doe" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Phone Number</label>
              <input required name="phone_number" onChange={handleChange} className="w-full p-3 bg-background/50 border border-white/10 rounded-xl focus:outline-none focus:border-primary transition-colors text-white" placeholder="+91 9876543210" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Email</label>
              <input required name="email" type="email" onChange={handleChange} className="w-full p-3 bg-background/50 border border-white/10 rounded-xl focus:outline-none focus:border-primary transition-colors text-white" placeholder="john@example.com" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Password</label>
              <input required name="password" type="password" onChange={handleChange} className="w-full p-3 bg-background/50 border border-white/10 rounded-xl focus:outline-none focus:border-primary transition-colors text-white" placeholder="••••••••" />
            </div>
          </div>

          <div className="pt-4 border-t border-white/10">
            <h3 className="text-lg font-medium mb-4 text-white/80">Emergency Contacts</h3>
            <p className="text-xs text-gray-500 mb-4">We require at least 2 emergency contacts for your safety.</p>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input required name="contact1_name" onChange={handleChange} className="w-full p-3 bg-background/50 border border-white/10 rounded-xl focus:outline-none focus:border-primary transition-colors text-white text-sm" placeholder="Contact 1 Name" />
                <input required name="contact1_phone" onChange={handleChange} className="w-full p-3 bg-background/50 border border-white/10 rounded-xl focus:outline-none focus:border-primary transition-colors text-white text-sm" placeholder="Contact 1 Phone" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input required name="contact2_name" onChange={handleChange} className="w-full p-3 bg-background/50 border border-white/10 rounded-xl focus:outline-none focus:border-primary transition-colors text-white text-sm" placeholder="Contact 2 Name" />
                <input required name="contact2_phone" onChange={handleChange} className="w-full p-3 bg-background/50 border border-white/10 rounded-xl focus:outline-none focus:border-primary transition-colors text-white text-sm" placeholder="Contact 2 Phone" />
              </div>
            </div>
          </div>

          <p className="text-xs text-gray-500 text-center leading-relaxed">
            By creating an account, you acknowledge that MindSenseAI is an AI wellness assistant and agree to our{" "}
            <Link href="/terms" className="text-primary hover:underline">Terms of Service</Link> and{" "}
            <Link href="/privacy" className="text-primary hover:underline">Privacy Policy</Link>.
          </p>

          <button disabled={loading} type="submit" className="w-full bg-gradient-to-r from-primary to-accent py-3 rounded-xl font-medium text-white hover:opacity-90 transition-opacity flex justify-center items-center">
            {loading ? "Creating Account..." : "Create Account"}
          </button>
        </form>
        
        <p className="text-center text-sm text-gray-400 mt-6">
          Already have an account? <Link href="/login" className="text-primary hover:underline">Log In</Link>
        </p>

        <div className="mt-8 pt-4 border-t border-white/5 flex justify-center gap-4 text-xs text-gray-500">
          <Link href="/safety" className="hover:text-gray-300 transition-colors">Crisis Support & Resources</Link>
        </div>
      </motion.div>
    </div>
  );
}