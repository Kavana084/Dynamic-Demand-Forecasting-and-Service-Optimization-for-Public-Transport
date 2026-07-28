import React, { useState } from 'react';
import { Button } from 'react-bootstrap';
import { MessageSquare, X } from 'lucide-react';
import ChatWidget from './ChatWidget';

const FloatingAssistant = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      zIndex: 1050,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-end'
    }}>
      {isOpen && (
        <div 
          className="mb-3 shadow-lg" 
          style={{ width: '350px', height: '500px', borderRadius: '12px', overflow: 'hidden', animation: 'fadeIn 0.2s ease-out' }}
        >
          <ChatWidget />
        </div>
      )}
      
      <Button 
        variant="primary" 
        className="rounded-circle shadow-lg d-flex align-items-center justify-content-center"
        style={{ width: '60px', height: '60px' }}
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <X size={28} /> : <MessageSquare size={28} />}
      </Button>

      <style>
        {`
          @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
          }
        `}
      </style>
    </div>
  );
};

export default FloatingAssistant;
