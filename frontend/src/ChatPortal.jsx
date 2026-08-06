import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { MessageSquare, LogOut, Send, PlusCircle } from 'lucide-react';

export default function ChatPortal({ token, onLogout }) {
  const [chats, setChats] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [targetTier, setTargetTier] = useState('Fast (8B)');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchChats();
  }, []);

  useEffect(() => {
    if (currentChatId) {
      fetchMessages(currentChatId);
    } else {
      setMessages([]);
    }
  }, [currentChatId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchChats = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/chats', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.status === 401) {
        onLogout();
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setChats(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchMessages = async (chatId) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/chats/${chatId}/messages`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.status === 401) {
        onLogout();
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const userMsg = { role: 'user', content: inputValue };
    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsLoading(true);

    const payload = {
      model: "llama-3.3-70b-versatile",
      messages: [...messages, userMsg].map(m => ({ role: m.role, content: m.content }))
    };

    try {
      const res = await fetch('http://127.0.0.1:8000/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-Model-Target': targetTier,
          'X-Chat-Id': currentChatId || 'null'
        },
        body: JSON.stringify(payload)
      });

      if (res.status === 401) {
        onLogout();
        return;
      }

      if (res.status === 403) {
        const errorData = await res.json();
        alert(`🚨 Request Blocked: ${errorData.detail || 'Policy Violation Detected'}`);
        return;
      }

      if (res.ok) {
        const data = await res.json();
        const returnedChatId = res.headers.get('X-Chat-Id');
        
        if (returnedChatId && returnedChatId !== currentChatId) {
          setCurrentChatId(returnedChatId);
          fetchChats();
        }
        
        if (data.choices && data.choices[0]) {
          setMessages(prev => [...prev, data.choices[0].message]);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const newChat = () => {
    setCurrentChatId(null);
  };

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 font-sans">
      
      {/* Sidebar */}
      <div className="w-64 bg-zinc-900 border-r border-zinc-800 flex flex-col">
        <div className="p-4 border-b border-zinc-800">
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
            PromptOps
          </h1>
        </div>
        
        <div className="p-4 border-b border-zinc-800">
          <button 
            onClick={newChat}
            className="w-full flex items-center justify-center gap-2 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded-lg py-2 transition-colors"
          >
            <PlusCircle size={18} />
            <span>New Chat</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          <div className="text-xs font-semibold text-zinc-500 mb-2 px-2 uppercase tracking-wider">
            Recent Chats
          </div>
          {chats.map(chat => (
            <button
              key={chat.id}
              onClick={() => setCurrentChatId(chat.id)}
              className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg truncate transition-colors ${
                currentChatId === chat.id ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
              }`}
            >
              <MessageSquare size={16} className="shrink-0" />
              <span className="truncate text-sm">{chat.title || 'New Chat'}</span>
            </button>
          ))}
        </div>

        <div className="p-4 border-t border-zinc-800">
          <button 
            onClick={onLogout}
            className="w-full flex items-center gap-2 text-zinc-400 hover:text-zinc-200 py-2"
          >
            <LogOut size={18} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <div className="h-16 border-b border-zinc-800 flex items-center justify-between px-6 bg-zinc-900/50 backdrop-blur-sm">
          <h2 className="font-medium text-zinc-200">
            {currentChatId ? chats.find(c => c.id === currentChatId)?.title || 'Chat' : 'New Chat'}
          </h2>
          
          <div className="flex items-center gap-2 text-sm">
            <span className="text-zinc-400">Model:</span>
            <select 
              value={targetTier}
              onChange={e => setTargetTier(e.target.value)}
              className="bg-zinc-800 border border-zinc-700 text-zinc-200 rounded-md py-1 px-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="Fast (8B)">Fast (8B)</option>
              <option value="Balanced (70B)">Balanced (70B)</option>
              <option value="Premium (405B)">Premium (405B)</option>
            </select>
          </div>
        </div>

        {/* Message List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-zinc-500">
              <MessageSquare size={48} className="mb-4 opacity-20" />
              <p>How can I help you today?</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div 
                  className={`max-w-3xl rounded-2xl px-5 py-4 ${
                    msg.role === 'user' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-zinc-800/80 border border-zinc-700/50 text-zinc-200 shadow-sm'
                  }`}
                >
                  <div className="prose prose-invert max-w-none">
                    {msg.role === 'user' ? (
                      <p className="whitespace-pre-wrap m-0">{msg.content}</p>
                    ) : (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-zinc-800/80 border border-zinc-700/50 text-zinc-400 rounded-2xl px-5 py-4 flex items-center gap-2">
                <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-zinc-900 border-t border-zinc-800">
          <form 
            onSubmit={handleSendMessage}
            className="max-w-4xl mx-auto relative flex items-center"
          >
            <input
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              placeholder="Message the assistant..."
              className="w-full bg-zinc-800 border border-zinc-700 rounded-full pl-6 pr-14 py-3.5 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 shadow-sm"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !inputValue.trim()}
              className="absolute right-2 p-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-full transition-colors flex items-center justify-center"
            >
              <Send size={18} className="mr-0.5 mt-0.5" />
            </button>
          </form>
          <div className="text-center text-xs text-zinc-500 mt-3">
            PromptOps Gateway intercepts all traffic to dynamically anonymize PII.
          </div>
        </div>
      </div>
    </div>
  );
}
