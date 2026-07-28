// Grok-compatible AI Service Architecture

import { aiAssistantChat } from '../api/client';

export class AIService {
  constructor() {
    this.sessionId = crypto.randomUUID();
    this.messageHistory = [];
  }

  async sendMessage(messageContent) {
    const userMessage = {
      role: 'user',
      content: messageContent,
      timestamp: new Date().toISOString(),
    };
    
    this.messageHistory.push(userMessage);

    try {
      const data = await aiAssistantChat(messageContent, this.sessionId);
      
      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        timestamp: new Date().toISOString(),
        toolUsed: data.tool_used,
        structuredData: data.structured_data,
      };

      this.messageHistory.push(assistantMessage);
      return assistantMessage;

    } catch (error) {
      console.error('AI Service Error:', error);
      throw error;
    }
  }

  getHistory() {
    return this.messageHistory;
  }
  
  clearHistory() {
    this.messageHistory = [];
    this.sessionId = crypto.randomUUID();
  }
}

export const aiService = new AIService();
