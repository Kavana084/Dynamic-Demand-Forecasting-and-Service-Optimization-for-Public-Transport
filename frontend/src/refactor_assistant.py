import re

file_path = 'f:/transit-ai-system/frontend/src/pages/passenger/TransitAIAssistant.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace emojis if any (currently there might not be emojis in TransitAIAssistant, wait, there's no emoji in it, but just in case)
content = content.replace("🤖", "<Bot size={28} />")

# Update to use aiService
import_statement = "import { aiService } from '../../services/aiService';\n"
content = content.replace("import { Send, Bot, User,", import_statement + "import { Send, Bot, User,")

# Replace fetch logic with aiService
fetch_logic = """
      const response = await fetch('http://localhost:8000/api/ai/assistant/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: sessionId,
        }),
      });

      const data = await response.json();

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        intent: data.intent,
        toolUsed: data.tool_used,
        structuredData: data.structured_data,
      };
"""

new_logic = """
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
"""

content = content.replace(fetch_logic, new_logic)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done refactoring TransitAIAssistant.jsx")
