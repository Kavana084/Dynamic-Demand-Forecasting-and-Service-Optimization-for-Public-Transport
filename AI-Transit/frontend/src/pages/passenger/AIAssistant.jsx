import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Clock, MapPin, Bus, AlertCircle } from 'lucide-react';
import clsx from 'clsx';
import { aiAssistantChat } from '../../api/client';

const suggestedPrompts = [
  'Plan a trip to Majestic',
  'How crowded is this route?',
  'How often do buses run?',
  'How long will it take?',
  'Will rain affect my trip?',
  'Do I need to change buses?',
];

export default function AIAssistant() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      from: 'bot',
      text: "Hello! I'm your Transit AI Assistant. I can help you with journey planning, crowd levels, travel times, and bus availability. Tell me where you'd like to travel.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;

    const userMessage = {
      id: messages.length + 1,
      from: 'user',
      text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await aiAssistantChat(text, sessionId);
      
      const botMessage = {
        id: messages.length + 2,
        from: 'bot',
        text: response.answer,
        timestamp: new Date(),
      };
      
      setMessages((prev) => [...prev, botMessage]);
      
      // Update session ID if provided
      if (response.session_id && !sessionId) {
        setSessionId(response.session_id);
      }
    } catch (error) {
      console.error('AI Assistant error:', error);
      const errorMessage = {
        id: messages.length + 2,
        from: 'bot',
        text: "I'm sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center">
            <Bot className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-ink">AI Transit Assistant</h2>
            <p className="text-sm text-muted">Your intelligent travel companion</p>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="flex-1 bg-surface border border-border rounded-2xl shadow-st-sm overflow-hidden flex flex-col">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={clsx(
                'flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300',
                message.from === 'user' ? 'flex-row-reverse' : 'flex-row'
              )}
            >
              <div
                className={clsx(
                  'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
                  message.from === 'user'
                    ? 'bg-primary text-white'
                    : 'bg-primary/10 text-primary'
                )}
              >
                {message.from === 'user' ? (
                  <User className="w-5 h-5" />
                ) : (
                  <Bot className="w-5 h-5" />
                )}
              </div>
              <div
                className={clsx(
                  'max-w-[70%] rounded-2xl px-4 py-3',
                  message.from === 'user'
                    ? 'bg-primary text-white rounded-tr-sm'
                    : 'bg-background border border-border text-ink rounded-tl-sm'
                )}
              >
                <p className="text-sm leading-relaxed">{message.text}</p>
                <p
                  className={clsx(
                    'text-xs mt-2',
                    message.from === 'user' ? 'text-white/70' : 'text-muted'
                  )}
                >
                  {formatTime(message.timestamp)}
                </p>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
                <Bot className="w-5 h-5" />
              </div>
              <div className="bg-background border border-border rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Prompts */}
        {messages.length === 1 && (
          <div className="px-6 pb-4 border-t border-border bg-background/50">
            <p className="text-xs font-semibold text-muted mb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              Suggested questions
            </p>
            <div className="flex flex-wrap gap-2">
              {suggestedPrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => setInput(prompt)}
                  className="st-focusable rounded-full border border-border bg-surface px-3 py-1.5 text-xs font-medium text-ink hover:bg-background hover:border-primary/30 smooth-transition"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="p-4 border-t border-border bg-surface">
          <div className="flex gap-3">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything about your journey..."
              className="flex-1 rounded-xl px-4 py-3 bg-background border border-border text-ink placeholder:text-muted focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 smooth-transition"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isTyping}
              className={clsx(
                'rounded-xl px-4 py-3 flex items-center gap-2 font-medium smooth-transition',
                !input.trim() || isTyping
                  ? 'bg-muted text-muted-2 cursor-not-allowed'
                  : 'bg-primary text-white hover:bg-primary-hover'
              )}
            >
              <Send className="w-5 h-5" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </div>
          <p className="text-xs text-muted mt-2 text-center">
            AI Assistant uses existing backend APIs to provide real-time transit information
          </p>
        </div>
      </div>
    </div>
  );
}
