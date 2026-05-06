"use client";
import { useAuth } from "../../hooks/useAuth";
import { User, Bell, Plus, Trash2, Save, Edit2, Check, X, Phone, Shield, ChevronRight } from "lucide-react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import api from "../../lib/api";

interface Contact {
  name: string;
  phone_number: string;
  callmebot_key?: string;
}

interface EditingContact extends Contact {
  index: number;
}

export default function ProfilePage() {
  const { user, checkAuth } = useAuth();

  const [contacts, setContacts] = useState<Contact[]>([]);
  const [editingContact, setEditingContact] = useState<EditingContact | null>(null);
  const [addingNew, setAddingNew] = useState(false);
  const [newContact, setNewContact] = useState<Contact>({ name: "", phone_number: "", callmebot_key: "" });
  const [saving, setSaving] = useState(false);
  const [deletingIndex, setDeletingIndex] = useState<number | null>(null);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (user?.emergency_contacts) {
      setContacts(user.emergency_contacts.map(c => ({ name: c.name, phone_number: c.phone_number, callmebot_key: (c as any).callmebot_key || "" })));
    }
  }, [user]);


  const showSuccess = (msg: string) => { setSuccessMsg(msg); setTimeout(() => setSuccessMsg(""), 4000); };
  const showError = (msg: string) => { setErrorMsg(msg); setTimeout(() => setErrorMsg(""), 4000); };

  const saveContacts = async (updatedContacts: Contact[]) => {
    setSaving(true);
    try {
      await api.put("/emergency-contacts", { contacts: updatedContacts });
      await checkAuth();
      setContacts(updatedContacts);
      showSuccess("Contact saved successfully!");
    } catch (err: any) {
      showError(err?.response?.data?.detail || "Failed to save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  // --- Per-contact Edit ---
  const startEdit = (i: number) => {
    setAddingNew(false);
    setEditingContact({ index: i, name: contacts[i].name, phone_number: contacts[i].phone_number });
  };

  const cancelEdit = () => setEditingContact(null);

  const saveEdit = async () => {
    if (!editingContact) return;
    if (!editingContact.name.trim() || !editingContact.phone_number.trim()) {
      showError("Both name and phone number are required.");
      return;
    }
    const updated = contacts.map((c, i) =>
      i === editingContact.index ? { name: editingContact.name.trim(), phone_number: editingContact.phone_number.trim() } : c
    );
    await saveContacts(updated);
    setEditingContact(null);
  };

  // --- Delete contact ---
  const deleteContact = async (i: number) => {
    if (contacts.length <= 1) { showError("You must keep at least 1 emergency contact."); return; }
    setDeletingIndex(i);
    const updated = contacts.filter((_, idx) => idx !== i);
    await saveContacts(updated);
    setDeletingIndex(null);
  };

  // --- Add new contact ---
  const saveNewContact = async () => {
    if (!newContact.name.trim() || !newContact.phone_number.trim()) {
      showError("Both name and phone number are required.");
      return;
    }
    const updated = [...contacts, { name: newContact.name.trim(), phone_number: newContact.phone_number.trim() }];
    await saveContacts(updated);
    setNewContact({ name: "", phone_number: "" });
    setAddingNew(false);
  };

  if (!user) return (
    <div className="min-h-screen bg-[#0a0a0f] text-white flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-[#1e293b] border-r border-white/10 flex-col p-6 hidden md:flex">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
            <span className="font-bold text-white">M</span>
          </div>
          <span className="font-bold text-xl tracking-wide text-white">MindSense</span>
        </div>
        <nav className="flex-1 space-y-1">
          {[
            { href: "/dashboard", label: "Dashboard" },
            { href: "/chat", label: "AI Chat" },
            { href: "/profile", label: "Profile", active: true },
            { href: "/settings", label: "Settings" },
          ].map(item => (
            <Link key={item.href} href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-colors ${
                item.active ? "bg-blue-600/20 text-blue-400 font-medium" : "text-gray-400 hover:bg-white/5 hover:text-white"
              }`}>
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      {/* Content */}
      <main className="flex-1 p-6 md:p-10 overflow-y-auto text-white">
        <h1 className="text-3xl font-bold text-white mb-8">Your Profile</h1>

        <div className="max-w-2xl space-y-5">

          {/* Toast Messages */}
          <AnimatePresence mode="wait">
            {successMsg && (
              <motion.div key="success" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="flex items-center gap-2 bg-green-500/15 border border-green-500/30 text-green-300 px-4 py-3 rounded-xl text-sm">
                <Check size={16} className="flex-shrink-0" /> {successMsg}
              </motion.div>
            )}
            {errorMsg && (
              <motion.div key="error" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="flex items-center gap-2 bg-red-500/15 border border-red-500/30 text-red-300 px-4 py-3 rounded-xl text-sm">
                <X size={16} className="flex-shrink-0" /> {errorMsg}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Profile Card */}
          <div className="bg-[#1e293b] border border-white/10 rounded-3xl p-6 flex items-center gap-5">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-2xl font-bold text-white flex-shrink-0 shadow-lg">
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <h2 className="text-xl font-bold text-white truncate">{user.full_name}</h2>
              <p className="text-gray-400 text-sm flex items-center gap-1.5 mt-0.5"><User size={13} className="flex-shrink-0"/> {user.email}</p>
              <p className="text-gray-400 text-sm flex items-center gap-1.5 mt-0.5"><Phone size={13} className="flex-shrink-0"/> {user.phone_number}</p>
            </div>
          </div>

          {/* Emergency Contacts */}
          <div className="bg-[#1e293b] border border-white/10 rounded-3xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-red-500/15 flex items-center justify-center">
                  <Bell size={16} className="text-red-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white">Emergency Contacts</h3>
                  <p className="text-xs text-gray-500">{contacts.length} contact{contacts.length !== 1 ? "s" : ""} · SMS alerts on crisis</p>
                </div>
              </div>
              <button
                onClick={() => { setEditingContact(null); setAddingNew(true); setNewContact({ name: "", phone_number: "" }); }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-400 hover:text-white bg-blue-600/10 hover:bg-blue-600 border border-blue-500/30 hover:border-blue-600 rounded-lg transition-all"
              >
                <Plus size={14} /> Add Contact
              </button>
            </div>

            {/* Contact List */}
            <div className="divide-y divide-white/5">
              <AnimatePresence>
                {contacts.map((c, i) => (
                  <motion.div key={`contact-${i}`}
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, height: 0 }}
                    className="px-6 py-4"
                  >
                    {editingContact?.index === i ? (
                      <div className="space-y-3">
                        <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-3">Editing Contact {i + 1}</p>
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="text-xs text-gray-500 mb-1 block">Name</label>
                            <input autoFocus value={editingContact.name}
                              onChange={e => setEditingContact({ ...editingContact, name: e.target.value })}
                              onKeyDown={e => e.key === 'Enter' && saveEdit()}
                              placeholder="e.g. Srujana"
                              className="w-full bg-black/30 border border-blue-500/40 rounded-xl px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-colors" />
                          </div>
                          <div>
                            <label className="text-xs text-gray-500 mb-1 block">Phone Number</label>
                            <input value={editingContact.phone_number}
                              onChange={e => setEditingContact({ ...editingContact, phone_number: e.target.value })}
                              placeholder="+91 98765 43210" type="tel"
                              className="w-full bg-black/30 border border-blue-500/40 rounded-xl px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-colors" />
                          </div>
                        </div>
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">💬 WhatsApp Key <span className="text-gray-600">(optional — for free WhatsApp alerts)</span></label>
                          <input value={editingContact.callmebot_key || ""}
                            onChange={e => setEditingContact({ ...editingContact, callmebot_key: e.target.value })}
                            placeholder="e.g. 123456"
                            className="w-full bg-black/30 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-green-500/60 transition-colors" />
                          <p className="text-xs text-gray-600 mt-1">They save +34644597621 on WhatsApp → send "I allow callmebot to send me messages" → share the key they receive</p>
                        </div>
                        <div className="flex items-center gap-2 justify-end pt-1">
                          <button onClick={cancelEdit} className="px-3 py-1.5 text-xs text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors">Cancel</button>
                          <button onClick={saveEdit} disabled={saving}
                            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors disabled:opacity-50">
                            {saving ? <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" /> : <Save size={13} />} Save
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* ---- VIEW MODE ---- */
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-600 to-slate-700 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
                          {c.name.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-white truncate">{c.name}</p>
                          <p className="text-xs text-gray-400 flex items-center gap-1 mt-0.5">
                            <Phone size={11} className="text-gray-500 flex-shrink-0" /> {c.phone_number}
                          </p>
                          {c.callmebot_key
                            ? null
                            : null
                          }
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <button
                            onClick={() => startEdit(i)}
                            title="Edit contact"
                            className="p-2 rounded-lg text-gray-500 hover:text-blue-400 hover:bg-blue-500/10 transition-colors"
                          >
                            <Edit2 size={15} />
                          </button>
                          <button
                            onClick={() => deleteContact(i)}
                            title="Delete contact"
                            disabled={deletingIndex === i}
                            className="p-2 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-40"
                          >
                            {deletingIndex === i
                              ? <div className="w-3.5 h-3.5 border border-red-400 border-t-transparent rounded-full animate-spin" />
                              : <Trash2 size={15} />
                            }
                          </button>
                        </div>
                      </div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Empty state */}
              {contacts.length === 0 && !addingNew && (
                <div className="px-6 py-8 text-center text-gray-600 text-sm">
                  No emergency contacts yet. Add one above.
                </div>
              )}

              {/* Add new contact form */}
              <AnimatePresence>
                {addingNew && (
                  <motion.div key="new-contact"
                    initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                    className="px-6 py-4 bg-blue-600/5 border-t border-blue-500/15"
                  >
                    <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-3">New Contact</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs text-gray-500 mb-1 block">Name</label>
                        <input
                          autoFocus
                          value={newContact.name}
                          onChange={e => setNewContact({ ...newContact, name: e.target.value })}
                          onKeyDown={e => e.key === 'Enter' && saveNewContact()}
                          placeholder="e.g. Srujana"
                          className="w-full bg-black/30 border border-blue-500/40 rounded-xl px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-colors"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 mb-1 block">Phone Number</label>
                        <input
                          value={newContact.phone_number}
                          onChange={e => setNewContact({ ...newContact, phone_number: e.target.value })}
                          onKeyDown={e => e.key === 'Enter' && saveNewContact()}
                          placeholder="+91 98765 43210"
                          type="tel"
                          className="w-full bg-black/30 border border-blue-500/40 rounded-xl px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-colors"
                        />
                      </div>
                    </div>
                    <div className="flex items-center gap-2 justify-end mt-3">
                      <button onClick={() => setAddingNew(false)} className="px-3 py-1.5 text-xs text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors">
                        Cancel
                      </button>
                      <button
                        onClick={saveNewContact}
                        disabled={saving}
                        className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors disabled:opacity-50"
                      >
                        {saving ? <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" /> : <Check size={13} />}
                        Add Contact
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Footer note */}
            <div className="px-6 py-3 border-t border-white/5 bg-black/10">
              <p className="text-xs text-gray-600 flex items-center gap-1.5">
                <Shield size={11} className="flex-shrink-0" />
                These contacts receive an SMS alert when a crisis is detected. Use international format (+91...).
              </p>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}