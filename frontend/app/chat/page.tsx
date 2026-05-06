"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "../../hooks/useAuth";
import api from "../../lib/api";
import { Send, Mic, Square, Paperclip, Volume2, Camera, X, AlertTriangle, Plus, MessageSquare, Menu, MoreVertical, Edit2, Trash2, Download, Check, LogOut } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Webcam from "react-webcam";
import Link from "next/link";

const LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'Hindi' },
  { code: 'kn', name: 'Kannada' },
  { code: 'ta', name: 'Tamil' },
  { code: 'te', name: 'Telugu' },
  { code: 'ml', name: 'Malayalam' },
  { code: 'mr', name: 'Marathi' },
  { code: 'bn', name: 'Bengali' },
  { code: 'gu', name: 'Gujarati' },
  { code: 'pa', name: 'Punjabi' },
  { code: 'ur', name: 'Urdu' },
];

export default function ChatPage() {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState("en");
  const [isRecording, setIsRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [isVideoRecording, setIsVideoRecording] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [openMenuId, setOpenMenuId] = useState<number | null>(null);
  const [editingSessionId, setEditingSessionId] = useState<number | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [detectedEmotion, setDetectedEmotion] = useState<string | null>(null);

  const videoRecorderRef = useRef<MediaRecorder | null>(null);
  const videoChunksRef = useRef<Blob[]>([]);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const webcamRef = useRef<Webcam>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await api.get("/chat/sessions");
        setSessions(res.data);
        if (res.data.length > 0) {
          setActiveSessionId(res.data[0].id);
        }
      } catch (err) {
        console.error("Failed to load sessions", err);
      }
    };
    fetchSessions();
  }, []);

  useEffect(() => {
    const fetchMessages = async () => {
      if (!activeSessionId) {
        setMessages([]);
        return;
      }
      try {
        const res = await api.get(`/chat/sessions/${activeSessionId}`);
        setMessages(res.data.messages || []);
      } catch (err) {
        console.error("Failed to load messages", err);
      }
    };
    fetchMessages();
  }, [activeSessionId]);

  const handleInput = () => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = "auto";
    textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px";
  };

  const handleDeleteSession = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.delete(`/chat/sessions/${id}`);
      setSessions(prev => prev.filter(s => s.id !== id));
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([]);
      }
    } catch (err) {
      showError("Failed to delete chat.");
    }
    setOpenMenuId(null);
  };

  const handleRenameSession = async (id: number) => {
    if (!editingTitle.trim()) return;
    try {
      await api.put(`/chat/sessions/${id}`, { title: editingTitle.trim() });
      setSessions(prev => prev.map(s => s.id === id ? { ...s, title: editingTitle.trim() } : s));
    } catch (err) {
      showError("Failed to rename chat.");
    }
    setEditingSessionId(null);
    setOpenMenuId(null);
  };

  const handleDownloadSession = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setOpenMenuId(null);
    try {
      const res = await api.get(`/chat/sessions/${id}`);
      const sessionData = res.data;
      if (!sessionData || !sessionData.messages) return;

      const textContent = sessionData.messages.map((m: any) => 
        `${m.role === 'user' ? 'You' : 'MindSense AI'}: ${m.content}\n\n`
      ).join("");

      const blob = new Blob([textContent], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${sessionData.title || 'chat'}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      showError("Failed to download chat.");
    }
  };

  const showError = (msg: string) => {
    setErrorMsg(msg);
    setTimeout(() => setErrorMsg(null), 5000);
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: "user", content: input.trim() };
    const updated = [...messages, userMessage];

    setMessages(updated);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setLoading(true);

    try {
      const res = await api.post("/chat", { 
        message: userMessage.content, 
        history: updated.slice(-6), 
        language, 
        session_id: activeSessionId,
        emotion_context: detectedEmotion 
      });
      setDetectedEmotion(null); // clear emotion after sending
      if (res.data && res.data.reply) {
        setMessages(prev => [...prev, { role: "assistant", content: res.data.reply }]);
        if (res.data.session_id && res.data.session_id !== activeSessionId) {
           setActiveSessionId(res.data.session_id);
           const sessRes = await api.get("/chat/sessions");
           setSessions(sessRes.data);
        }
      } else {
        throw new Error("Invalid response format");
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: "I'm sorry, I encountered an error connecting to the AI system. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: any) => {
    const file = e.target.files[0];
    if (!file) return;

    const fd = new FormData();
    fd.append("file", file);

    const isVideo = file.name.match(/\.(mp4|mov|avi|webm)$/i);
    const endpoint = isVideo ? "/upload-video" : "/upload";

    setLoading(true);
    try {
      const res = await api.post(endpoint, fd);
      if (res.data.type === "text" && res.data.content) {
        setInput(prev => prev + (prev ? "\n\n" : "") + res.data.content);
        handleInput();
      } else if ((res.data.type === "video" || res.data.message) && res.data.message) {
        setMessages(prev => [...prev, { role: "assistant", content: res.data.message }]);
      } else {
        throw new Error(res.data.error || "Upload failed");
      }
    } catch (err: any) {
      showError(err.message || "Failed to process file upload.");
    } finally {
      setLoading(false);
      if (e.target) e.target.value = null; // reset file input
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const file = new File([blob], "recording.webm", { type: "audio/webm" });
        const fd = new FormData();
        fd.append("file", file);

        setLoading(true);
        try {
          const res = await api.post("/transcribe", fd, {
            headers: { "Content-Type": "multipart/form-data" },
          });
          if (res.data && res.data.text) {
             setInput(prev => prev + (prev ? " " : "") + res.data.text);
             handleInput();
          } else {
            showError("Recording captured but no speech detected. Please try again.");
          }
        } catch (err: any) {
          const detail = err?.response?.data?.detail || err?.message || "Unknown error";
          console.error("Transcription error:", detail);
          showError(`Transcription failed: ${detail}`);
        } finally {
          setLoading(false);
          stream.getTracks().forEach(track => track.stop());
        }
      };

      recorder.start();
      setIsRecording(true);
    } catch {
      showError("Microphone permission denied or not available.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const playTTS = async (text: string) => {
    try {
      const res = await api.post("/tts", { text, language }, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const audio = new Audio(url);
      audio.play();
    } catch {
      showError("Failed to play text-to-speech audio.");
    }
  };

  const startVideoRecording = () => {
    if (webcamRef.current && webcamRef.current.stream) {
      try {
        const stream = webcamRef.current.stream;
        const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
        videoRecorderRef.current = recorder;
        videoChunksRef.current = [];

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) videoChunksRef.current.push(e.data);
        };

        recorder.onstop = async () => {
          const blob = new Blob(videoChunksRef.current, { type: 'video/webm' });
          const file = new File([blob], "video.webm");
          const fd = new FormData();
          fd.append("file", file);
          setLoading(true);
          setShowCamera(false);
          try {
              const res = await api.post("/upload-video", fd);
              const emotion = res.data?.emotion || "neutral";
              setDetectedEmotion(emotion);

              // Add a user-visible status message
              const statusMsg = { role: "assistant", content: `📷 *Facial emotion detected: **${emotion}***` };
              setMessages(prev => [...prev, statusMsg]);

              // Automatically send to AI so it responds based on the detected emotion
              const autoMessage = `I just shared my video. My detected facial emotion is "${emotion}". Please respond to how I'm feeling.`;
              const chatHistory = [...messages, statusMsg];

              const chatRes = await api.post("/chat", {
                message: autoMessage,
                history: chatHistory.slice(-6),
                language,
                session_id: activeSessionId,
                emotion_context: emotion
              });

              if (chatRes.data?.reply) {
                setMessages(prev => [...prev, { role: "assistant", content: chatRes.data.reply }]);
                if (chatRes.data.session_id && chatRes.data.session_id !== activeSessionId) {
                  setActiveSessionId(chatRes.data.session_id);
                  const sessRes = await api.get("/chat/sessions");
                  setSessions(sessRes.data);
                }
              }
              setDetectedEmotion(null); // clear after use
          } catch (err) {
              showError("Failed to process video emotion.");
          } finally {
              setLoading(false);
          }
        };


        recorder.start();
        setIsVideoRecording(true);
      } catch (err) {
        showError("Error starting video recording.");
      }
    }
  };

  const stopVideoRecording = () => {
    videoRecorderRef.current?.stop();
    setIsVideoRecording(false);
  };

  return (
    <div className="flex h-screen bg-[#0a0a0f] text-gray-100 font-sans overflow-hidden">
      {/* Sidebar */}
      <div className={`fixed md:static inset-y-0 left-0 z-40 w-64 bg-[#1e293b] border-r border-white/10 flex flex-col transition-transform transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <div className="p-4 border-b border-white/10 flex justify-between items-center">
          <button 
            onClick={() => {setActiveSessionId(null); setMessages([]); setSidebarOpen(false);}} 
            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white py-2.5 rounded-xl font-medium transition-colors shadow-md"
          >
            <Plus size={18}/> New Chat
          </button>
          <button className="md:hidden ml-2 p-2 text-gray-400 hover:text-white" onClick={() => setSidebarOpen(false)}>
            <X size={20} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {sessions.length === 0 ? (
            <div className="text-center text-gray-500 text-sm mt-10">No previous chats</div>
          ) : (
            sessions.map(s => (
              <div key={s.id} className={`w-full group relative rounded-lg mb-1 transition-colors ${activeSessionId === s.id ? 'bg-blue-600/20 text-blue-400' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'}`}>
                {editingSessionId === s.id ? (
                  <div className="flex items-center gap-2 px-3 py-3 w-full">
                    <input 
                      autoFocus
                      value={editingTitle} 
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleRenameSession(s.id)}
                      className="flex-1 bg-black/30 border border-white/20 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-blue-500"
                    />
                    <button onClick={() => handleRenameSession(s.id)} className="text-green-400 hover:text-green-300">
                      <Check size={16}/>
                    </button>
                    <button onClick={() => setEditingSessionId(null)} className="text-gray-400 hover:text-white">
                      <X size={16}/>
                    </button>
                  </div>
                ) : (
                  <>
                    <button 
                      onClick={() => { setActiveSessionId(s.id); setSidebarOpen(false); setOpenMenuId(null); }} 
                      className="w-full text-left px-3 py-3 flex items-center gap-3 pr-10"
                    >
                      <MessageSquare size={16} className="flex-shrink-0" />
                      <span className="truncate text-sm font-medium">{s.title}</span>
                    </button>
                    
                    <button 
                      onClick={(e) => { e.stopPropagation(); setOpenMenuId(openMenuId === s.id ? null : s.id); }}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-gray-500 hover:text-white rounded-md opacity-0 group-hover:opacity-100 transition-opacity focus:opacity-100 hover:bg-white/10"
                    >
                      <MoreVertical size={16} />
                    </button>

                    {openMenuId === s.id && (
                      <>
                        <div className="fixed inset-0 z-40" onClick={(e) => { e.stopPropagation(); setOpenMenuId(null); }} />
                        <div className="absolute right-2 top-10 w-36 bg-[#0f172a] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden py-1">
                          <button 
                            onClick={(e) => { e.stopPropagation(); setEditingTitle(s.title); setEditingSessionId(s.id); setOpenMenuId(null); }}
                            className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-white/10 flex items-center gap-2"
                          >
                            <Edit2 size={14}/> Rename
                          </button>
                          <button 
                            onClick={(e) => handleDownloadSession(s.id, e)}
                            className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-white/10 flex items-center gap-2"
                          >
                            <Download size={14}/> Download
                          </button>
                          <button 
                            onClick={(e) => handleDeleteSession(s.id, e)}
                            className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2"
                          >
                            <Trash2 size={14}/> Delete
                          </button>
                        </div>
                      </>
                    )}
                  </>
                )}
              </div>
            ))
          )}
        </div>

        {/* User Profile + Logout footer */}
        <div className="p-3 border-t border-white/10 flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
            <span className="text-white font-bold text-sm">{user?.full_name?.[0]?.toUpperCase() ?? 'U'}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-200 truncate">{user?.full_name ?? 'User'}</p>
            <p className="text-xs text-gray-500 truncate">{user?.email ?? ''}</p>
          </div>
          <button
            onClick={logout}
            title="Logout"
            className="p-2 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut size={17} />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 h-screen relative w-full">
        {/* Header */}
        <header className="flex-none p-4 md:px-8 border-b border-white/10 bg-[#1e293b]/50 backdrop-blur-md flex justify-between items-center z-10 sticky top-0">
          <div className="flex items-center gap-4">
            <button className="md:hidden p-2 text-gray-400 hover:text-white" onClick={() => setSidebarOpen(true)}>
              <Menu size={24} />
            </button>
            <Link href="/dashboard" className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center shadow-lg hover:opacity-90 transition-opacity">
              <span className="font-bold text-white text-lg font-serif">M</span>
            </Link>
          <div>
            <h1 className="font-bold text-white text-lg tracking-wide">MindSense AI</h1>
            <p className="text-xs text-green-400 flex items-center gap-1.5 font-medium">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]"></span> 
              Online & Secure
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <select 
            value={language} 
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-[#1e293b] border border-white/20 text-gray-200 text-sm rounded-lg p-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50 hover:bg-[#1e293b]/80 transition-colors cursor-pointer"
          >
            {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.name}</option>)}
          </select>
        </div>
      </header>

      {/* Error Toast */}
      <AnimatePresence>
        {errorMsg && (
          <motion.div 
            initial={{ opacity: 0, y: -20 }} 
            animate={{ opacity: 1, y: 0 }} 
            exit={{ opacity: 0, y: -20 }}
            className="absolute top-20 left-1/2 -translate-x-1/2 z-50 bg-red-500/90 text-white px-6 py-3 rounded-full flex items-center gap-2 shadow-2xl backdrop-blur-md"
          >
            <AlertTriangle size={18} />
            <span className="text-sm font-medium">{errorMsg}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth">
        <div className="max-w-4xl mx-auto w-full flex flex-col gap-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center text-center max-w-lg mx-auto opacity-70 mt-20">
              <div className="w-24 h-24 rounded-3xl bg-blue-500/10 flex items-center justify-center mb-8 border border-blue-500/20 shadow-[0_0_30px_rgba(59,130,246,0.1)]">
                <span className="text-5xl text-blue-400 font-serif">M</span>
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">How are you feeling today?</h2>
              <p className="text-gray-400 text-base leading-relaxed">
                Type a message, record your voice, or upload a document. I am a safe space here to listen, analyze, and help.
              </p>
            </div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((m, i) => (
              <motion.div 
                initial={{ opacity: 0, y: 15, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                key={i} 
                className={`flex w-full ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {m.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex-shrink-0 flex items-center justify-center mr-3 mt-1 shadow-md">
                    <span className="text-white text-xs font-bold font-serif">M</span>
                  </div>
                )}
                
                <div 
                  className={`group relative max-w-[85%] md:max-w-[75%] px-5 py-4 rounded-2xl shadow-sm text-[16px] leading-relaxed
                    ${m.role === 'user' 
                      ? 'bg-blue-600 text-white rounded-br-sm' 
                      : 'bg-[#1e293b] border border-white/10 text-gray-100 rounded-bl-sm'}`}
                >
                  <div className="whitespace-pre-wrap">{m.content}</div>
                  
                  {m.role === 'assistant' && (
                    <button 
                      onClick={() => playTTS(m.content)}
                      className="absolute -right-12 bottom-1 p-2 rounded-full bg-[#1e293b] border border-white/10 text-gray-400 hover:text-white hover:bg-blue-500/20 transition-all opacity-0 group-hover:opacity-100 shadow-lg"
                      title="Read aloud"
                    >
                      <Volume2 size={18} />
                    </button>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex w-full justify-start items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-[#1e293b] border border-white/10 flex items-center justify-center shadow-md">
                <span className="text-white text-xs font-bold font-serif opacity-50">M</span>
              </div>
              <div className="bg-[#1e293b] border border-white/10 px-5 py-4 rounded-2xl rounded-bl-sm flex gap-1.5 items-center">
                <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </motion.div>
          )}
          <div ref={chatEndRef} className="h-4" />
        </div>
      </main>

      {/* Camera Modal */}
      <AnimatePresence>
        {showCamera && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-[#0a0a0f]/90 backdrop-blur-sm flex items-center justify-center p-4"
          >
            <div className="bg-[#1e293b] rounded-3xl overflow-hidden max-w-2xl w-full relative border border-white/10 shadow-2xl">
              <button 
                onClick={() => setShowCamera(false)} 
                className="absolute top-4 right-4 z-10 p-2.5 bg-black/40 hover:bg-black/60 transition-colors rounded-full text-white backdrop-blur-md"
              >
                <X size={20}/>
              </button>
              
              <div className="bg-black relative aspect-video flex items-center justify-center">
                <Webcam audio={false} ref={webcamRef} screenshotFormat="image/jpeg" className="w-full h-full object-cover" />
                {isVideoRecording && (
                  <div className="absolute top-4 left-4 flex items-center gap-2 bg-red-500/80 backdrop-blur-md text-white px-3 py-1.5 rounded-full text-sm font-medium">
                    <span className="w-2 h-2 rounded-full bg-white animate-pulse"></span>
                    Recording
                  </div>
                )}
              </div>
              
              <div className="p-6 bg-[#1e293b] flex justify-center border-t border-white/5">
                <button 
                  onClick={isVideoRecording ? stopVideoRecording : startVideoRecording} 
                  className={`text-white rounded-full px-8 py-4 shadow-xl flex items-center gap-3 font-semibold transition-all transform hover:scale-105 active:scale-95 ${isVideoRecording ? 'bg-red-500 hover:bg-red-600' : 'bg-blue-600 hover:bg-blue-500'}`}
                >
                  {isVideoRecording ? <Square size={20}/> : <Camera size={20}/>} 
                  {isVideoRecording ? "Stop Recording" : "Record Video"}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Area */}
      <footer className="flex-none p-4 md:p-6 bg-[#0a0a0f] border-t border-white/10 z-10">
        <div className="max-w-4xl mx-auto w-full flex items-end gap-3 bg-[#1e293b]/80 border border-white/10 rounded-2xl p-2.5 shadow-xl focus-within:border-blue-500/50 focus-within:bg-[#1e293b] transition-all">
          
          <button 
            onClick={() => document.getElementById('fileUpload')?.click()}
            className="p-3 text-gray-400 hover:text-white rounded-xl hover:bg-white/10 transition-colors flex-shrink-0"
            title="Upload Document or Video (TXT, PDF, MP4)"
          >
            <Paperclip size={22} />
            <input type="file" id="fileUpload" className="hidden" accept=".txt,.pdf,.mp4,.mov,.avi,.webm" onChange={handleFileUpload} />
          </button>

          <button 
            onClick={() => setShowCamera(true)}
            className="p-3 text-gray-400 hover:text-white rounded-xl hover:bg-white/10 transition-colors flex-shrink-0 hidden sm:block"
            title="Use Webcam"
          >
            <Camera size={22} />
          </button>

          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => { setInput(e.target.value); handleInput(); }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="Type your message... (Shift+Enter for new line)"
            rows={1}
            className="flex-1 bg-transparent border-none text-white text-base focus:outline-none resize-none py-3 px-2 max-h-[200px] min-h-[48px] placeholder:text-gray-500"
          />

          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`p-3 rounded-xl transition-all flex-shrink-0 ${isRecording ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30' : 'text-gray-400 hover:text-white hover:bg-white/10'}`}
            title={isRecording ? "Stop Voice Recording" : "Start Voice Input"}
          >
            {isRecording ? <Square size={22} className="animate-pulse" /> : <Mic size={22} />}
          </button>

          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="p-3 rounded-xl bg-blue-600 text-white disabled:opacity-50 disabled:bg-gray-600 disabled:cursor-not-allowed hover:bg-blue-500 transition-colors flex-shrink-0 shadow-md"
            title="Send Message"
          >
            <Send size={22} />
          </button>
        </div>
        <div className="max-w-4xl mx-auto text-center mt-3">
          <p className="text-[11px] text-gray-500">MindSense AI can make mistakes. Consider verifying important mental health information.</p>
        </div>
      </footer>
      </div>
    </div>
  );
}