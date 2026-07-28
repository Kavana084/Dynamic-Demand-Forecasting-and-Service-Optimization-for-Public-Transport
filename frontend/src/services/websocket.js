export class TransitWebSocketService {
  constructor() {
    this.ws = null;
    this.listeners = [];
    this.reconnectAttempts = 0;
    this.maxReconnectDelay = 30000;
    this.pingInterval = null;
    this.intentionalDisconnect = false;
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    
    this.intentionalDisconnect = false;
    const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
    const wsBase = apiBase.startsWith('https://')
      ? apiBase.replace('https://', 'wss://')
      : apiBase.replace('http://', 'ws://');
    this.ws = new WebSocket(`${wsBase}/ws/transit`);
    
    this.ws.onopen = () => {
      console.log('WebSocket Connected');
      this.reconnectAttempts = 0;
      this.notifyListeners({ type: 'connection_status', status: 'connected' });
      
      // Start heartbeat
      if (this.pingInterval) clearInterval(this.pingInterval);
      this.pingInterval = setInterval(() => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000); // 30 seconds
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Ignore pong responses at the application level
        if (data.type === 'pong') return;
        this.notifyListeners(data);
      } catch (e) {
        console.error('Failed to parse websocket message', e);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket Disconnected');
      this.notifyListeners({ type: 'connection_status', status: 'disconnected' });
      this.cleanup();
      
      if (!this.intentionalDisconnect) {
        this.attemptReconnect();
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };
  }

  attemptReconnect() {
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxReconnectDelay);
    console.log(`Attempting to reconnect in ${delay}ms...`);
    this.reconnectAttempts++;
    setTimeout(() => {
      if (!this.intentionalDisconnect) {
        this.connect();
      }
    }, delay);
  }

  cleanup() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    this.ws = null;
  }

  disconnect() {
    this.intentionalDisconnect = true;
    if (this.ws) {
      this.ws.close();
      this.cleanup();
    }
  }

  subscribe(callback) {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback);
    };
  }

  notifyListeners(data) {
    this.listeners.forEach(callback => callback(data));
  }
}

export const wsService = new TransitWebSocketService();
