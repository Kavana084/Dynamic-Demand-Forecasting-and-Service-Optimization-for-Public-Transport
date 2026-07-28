import { useState, useRef, useEffect } from 'react';
import { aiService } from '../../services/aiService';
import { Send, Bot, User, Clock, X, Sparkles, MapPin, Navigation, ArrowRight, AlertTriangle } from 'lucide-react';

const SUGGESTED_QUESTIONS = [
  "How can I get to my destination?",
  "What is the best route available right now?",
  "When is the next bus arriving?",
  "Which routes are busiest today?",
  "Help me plan my journey.",
];

// Rich response card components
function JourneyCard({ data }) {
  if (!data || !data.success) return null;
  
  return (
    <div className="bg-gradient-to-r from-primary/10 to-accent-indigo/10 border border-primary/20 rounded-xl p-4 mt-3">
      <div className="flex items-center gap-2 mb-3">
        <Navigation className="w-4 h-4 text-primary" />
        <span className="text-sm font-semibold text-primary">Recommended Route</span>
      </div>
      <div className="flex items-center gap-2 text-sm text-ink mb-2">
        <span className="font-medium">{data.source}</span>
        <ArrowRight className="w-4 h-4 text-muted" />
        <span className="font-medium">{data.destination}</span>
      </div>
      <div className="grid grid-cols-3 gap-2 mt-3">
        <div className="bg-white/50 rounded-lg p-2 text-center">
          <p className="text-xs text-muted">ETA</p>
          <p className="text-sm font-bold text-ink">{data.eta_minutes} min</p>
        </div>
        <div className="bg-white/50 rounded-lg p-2 text-center">
          <p className="text-xs text-muted">Distance</p>
          <p className="text-sm font-bold text-ink">{data.distance_km || data.total_distance_km} km</p>
        </div>
        <div className="bg-white/50 rounded-lg p-2 text-center">
          <p className="text-xs text-muted">Transfers</p>
          <p className="text-sm font-bold text-ink">{data.transfers || 0}</p>
        </div>
      </div>
    </div>
  );
}

function AlternativeRoutesCard({ data }) {
  if (!data || !data.alternative_routes || data.alternative_routes.length === 0) return null;
  
  return (
    <div className="bg-surface border border-border rounded-xl p-4 mt-3">
      <div className="flex items-center gap-2 mb-3">
        <Navigation className="w-4 h-4 text-primary" />
        <span className="text-sm font-semibold text-ink">Alternative Routes</span>
      </div>
      <div className="space-y-2">
        {data.alternative_routes.map((route, idx) => (
          <div key={idx} className="bg-background rounded-lg p-3 border border-border">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-ink">{route.strategy}</span>
              <span className="text-xs text-muted">{route.eta} min</span>
            </div>
            <div className="flex gap-3 text-xs text-muted">
              <span>{route.distance} km</span>
              <span>{route.transfers} transfers</span>
              <span>{route.walking_distance}m walk</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function TransitAIAssistant() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: "Hi! I'm your AI Transit Assistant. I can help you plan journeys, check bus arrivals, find alternative routes, and more. How can I help you today?",
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const assistantMessageData = await aiService.sendMessage(userMessage.content);
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: assistantMessageData.content,
        timestamp: new Date(),
        intent: assistantMessageData.intent,
        toolUsed: assistantMessageData.toolUsed,
        structuredData: assistantMessageData.structuredData,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: "I'm sorry, I couldn't connect to the server. Please try again.",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestedQuestion = (question) => {
    setInput(question);
    inputRef.current?.focus();
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary to-accent-indigo text-white p-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur-sm">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">AI Transit Assistant</h1>
              <p className="text-white/80 text-sm">Your intelligent travel companion</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Chat Area */}
          <div className="lg:col-span-3">
            <div className="modern-card h-[calc(100vh-280px)] flex flex-col">
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl p-4 ${
                        message.role === 'user'
                          ? 'bg-primary text-white'
                          : 'bg-surface border border-border text-ink'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {message.role === 'assistant' && (
                          <div className="w-8 h-8 bg-primary/10 rounded-xl flex items-center justify-center shrink-0">
                            <Bot className="w-4 h-4 text-primary" />
                          </div>
                        )}
                        <div className="flex-1">
                          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                          
                          {/* Rich response cards */}
                          {message.toolUsed === 'plan_trip' && message.structuredData && (
                            <JourneyCard data={message.structuredData} />
                          )}
                          {message.toolUsed === 'get_alternative_routes' && message.structuredData && (
                            <AlternativeRoutesCard data={message.structuredData} />
                          )}
                          
                          <div className="flex items-center gap-2 mt-2">
                            <Clock className="w-3 h-3 opacity-60" />
                            <span className="text-xs opacity-60">{formatTime(message.timestamp)}</span>
                          </div>
                        </div>
                        {message.role === 'user' && (
                          <div className="w-8 h-8 bg-white/20 rounded-xl flex items-center justify-center shrink-0">
                            <User className="w-4 h-4" />
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-surface border border-border rounded-2xl p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-primary/10 rounded-xl flex items-center justify-center">
                          <Bot className="w-4 h-4 text-primary" />
                        </div>
                        <div className="flex gap-1">
                          <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="border-t border-border p-4">
                <div className="flex gap-3">
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Type your message..."
                    className="flex-1 bg-background border border-border rounded-xl px-4 py-3 text-ink focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 smooth-transition"
                    disabled={isLoading}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!input.trim() || isLoading}
                    className="bg-primary text-white px-6 py-3 rounded-xl font-semibold hover:bg-primary-hover disabled:bg-muted disabled:cursor-not-allowed smooth-transition flex items-center gap-2"
                  >
                    <Send className="w-4 h-4" />
                    Send
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Suggested Questions */}
          <div className="lg:col-span-1">
            <div className="modern-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-5 h-5 text-primary" />
                <h3 className="font-bold text-ink">Suggested Questions</h3>
              </div>
              <div className="space-y-2">
                {SUGGESTED_QUESTIONS.map((question, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestedQuestion(question)}
                    className="w-full text-left p-3 rounded-xl bg-surface border border-border hover:border-primary hover:bg-primary/5 smooth-transition text-sm text-ink transition-colors"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>

            {/* Info Card */}
            <div className="modern-card p-5 mt-4">
              <h3 className="font-bold text-ink mb-3">About</h3>
              <p className="text-sm text-muted">
                I use AI to understand your questions and provide real-time transit information. 
                All data comes from live backend services.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
