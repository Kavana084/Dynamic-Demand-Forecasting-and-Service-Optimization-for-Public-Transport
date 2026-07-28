import React, { useState } from 'react';
import { Card, Form, Button, InputGroup } from 'react-bootstrap';
import { Send } from 'lucide-react';
import { aiAssistantChat } from '../api/client';
const ChatWidget = () => {
  const [messages, setMessages] = useState([
    { text: "Hello! I am your AI Transit Assistant. How can I help you today?", isBot: true }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim()) return;

    const userMessage = input;
    setMessages(prev => [...prev, { text: userMessage, isBot: false }]);
    setInput('');
    setIsLoading(true);

    console.log("CHAT_REQUEST", userMessage);

    try {
      // API call to backend
      const response = await aiAssistantChat(userMessage, sessionId);
      setMessages(prev => [...prev, { text: response.answer || "I received your message.", isBot: true }]);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || "Sorry, I am having trouble connecting to the server.";
      setMessages(prev => [...prev, { text: errorMsg, isBot: true, isError: true }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setInput(suggestion);
  };

  return (
    <Card className="shadow-sm border-0 h-100 d-flex flex-column">
      <Card.Header className="bg-white border-bottom">
        <h5 className="mb-0">Chat with AI</h5>
      </Card.Header>
      
      <Card.Body className="overflow-auto flex-grow-1" style={{ maxHeight: '400px' }}>
        {messages.map((msg, idx) => (
          <div key={idx} className={`mb-3 d-flex ${msg.isBot ? 'justify-content-start' : 'justify-content-end'}`}>
            <div 
              className={`p-3 rounded-3 ${msg.isBot ? 'bg-light text-dark' : 'bg-primary text-white'}`}
              style={{ maxWidth: '80%' }}
            >
              {msg.text}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="mb-3 d-flex justify-content-start">
            <div className="p-3 rounded-3 bg-light text-dark text-muted">
              Typing...
            </div>
          </div>
        )}
      </Card.Body>

      <Card.Footer className="bg-white border-top">
        <div className="mb-2 d-flex flex-wrap gap-2">
          <BadgeButton onClick={() => handleSuggestionClick("Which route has the highest demand?")}>
            Highest Demand Route?
          </BadgeButton>
          <BadgeButton onClick={() => handleSuggestionClick("Why did the optimizer allocate more buses to Route 5?")}>
            Route 5 Allocation?
          </BadgeButton>
        </div>
        <Form onSubmit={handleSend}>
          <InputGroup>
            <Form.Control
              placeholder="Ask a question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
            />
            <Button variant="primary" type="submit" disabled={isLoading || !input.trim()}>
              <Send size={18} />
            </Button>
          </InputGroup>
        </Form>
      </Card.Footer>
    </Card>
  );
};

const BadgeButton = ({ children, onClick }) => (
  <span 
    className="badge bg-secondary bg-opacity-10 text-secondary p-2 cursor-pointer border" 
    style={{ cursor: 'pointer' }}
    onClick={onClick}
  >
    {children}
  </span>
);

export default ChatWidget;
