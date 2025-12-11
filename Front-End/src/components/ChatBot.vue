<template>
  <div class="chat-overlay">
    <div class="chat-container">
      <!-- Chat History Sidebar -->
      <div class="chat-sidebar">
        <h3>Chat History</h3>
        <button class="new-session-btn" @click="startNewSession">➕ New Session</button>
        <ul>
          <li 
            v-for="(chat, index) in chatHistory" 
            :key="chat.id"
            @click="loadChat(chat.id)"
            :class="{ active: chat.id === activeSession }"
          >
            {{ chat.name }}
            <button @click.stop="deleteChat(chat.id)">🗑</button>
          </li>
        </ul>
      </div>

      <!-- Chat Window -->
      <div class="chat-window">
        <div class="chat-header">
          <h2>AI Chatbot - {{ activeSession ? `Session ${activeSession}` : "New Chat" }}</h2>
          <button @click="$emit('closeChat')" class="close-btn">✖</button>
        </div>

        <div class="chat-messages" ref="chatMessages">
          <p v-for="(msg, index) in messages" :key="index" :class="['message', msg.sender]">
            <strong>{{ msg.sender }}:</strong> {{ msg.message }}
          </p>
          <p v-if="isTyping" class="message bot typing">
            <strong>bot:</strong> <span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>
          </p>
        </div>

        <div class="chat-input">
          <input v-model="newMessage" placeholder="Type your message..." @keyup.enter="sendMessage" />
          <button @click="sendMessage">Send</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from "@/utils/auth";

export default {
  data() {
    return {
      messages: [],
      newMessage: "",
      chatHistory: [],
      activeSession: null,
      isTyping: false, // Typing animation
    };
  },
  mounted() {
    this.fetchChatHistory();
  },
  methods: {
    async fetchChatHistory() {
      try {
        const response = await api.get("/all_chat_sessions");
        console.log("Chat History Response:", response.data); // Debugging
        this.chatHistory = response.data.sessions.map(session => ({
          id: session.id,
          name: `Session ${session.id}`
        }));
      } catch (error) {
        console.error("Error fetching chat history:", error);
      }
    },

    async loadChat(sessionId) {
        this.activeSession = sessionId;
        try {
          const response = await api.get(`/chat/history/${sessionId}`);
          console.log("Chat Messages:", response.data); // Debugging
          this.messages = response.data.chat_history
          this.scrollToBottom();
        } catch (error) {
          console.error("Error loading chat:", error);
        }
      },

    async startNewSession() {
      this.activeSession = null;
      this.messages = [];
    },

    async sendMessage() {
      if (!this.newMessage.trim()) return;      
      const messageData = { message: this.newMessage, session_id: this.activeSession };
      this.messages.push({ sender: "user", message: this.newMessage });
      this.isTyping = true; // Show typing animation
      this.newMessage = "";
      this.scrollToBottom();
      try {
        const response = await api.post("/chat", messageData);        
        // If a new session is created, update activeSession
        if (!this.activeSession) {
          this.activeSession = response.data.session[0].id;
          this.chatHistory.unshift({
            id: this.activeSession,
            name: `Session ${this.activeSession}`
          });
        }
        setTimeout(() => {
          this.isTyping = false;
          this.messages.push({ sender: "bot", message: response.data.response });
          this.scrollToBottom();
        }, 1000);
        this.newMessage = "";
      } catch (error) {
        console.error("Error sending message:", error);
        this.isTyping = false;
      }
    },

    async deleteChat(sessionId) {
      try {
        await api.delete(`/delete_session/${sessionId}`);
        this.chatHistory = this.chatHistory.filter(chat => chat.id !== sessionId);
        if (this.activeSession === sessionId) {
          this.messages = [];
          this.activeSession = null;
        }
      } catch (error) {
        console.error("Error deleting chat session:", error);
      }
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const chatContainer = this.$refs.chatMessages;
        if (chatContainer) {
          chatContainer.scrollTop = chatContainer.scrollHeight;
        }
      });
    }
  }
};
</script>

<style scoped>
.chat-overlay {
  position: fixed;
  top: 5%;
  left: 5%;
  width: 90%;
  height: 90%;
  z-index: 2000;
  background: rgb(30, 27, 27);
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 20px;
}

.chat-container {
  display: flex;
  width: 85%;
  height: 85%;
  background: #222;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.chat-sidebar {
  width: 25%;
  background: #111;
  color: white;
  padding: 20px;
  overflow-y: auto;
}

.chat-sidebar h3 {
  margin-bottom: 15px;
}

.new-session-btn {
  display: block;
  width: 100%;
  padding: 10px;
  background: #3498db;
  color: white;
  border: none;
  cursor: pointer;
  margin-bottom: 10px;
  border-radius: 5px;
}

.chat-sidebar ul {
  list-style: none;
  padding: 0;
}

.chat-sidebar li {
  padding: 10px;
  border-bottom: 1px solid #333;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-sidebar li.active {
  background: #444;
}

.chat-window {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #333;
  color: white;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  padding: 15px;
  background: #636364;
  color: white;
}

.close-btn {
  background: transparent;
  border: none;
  color: white;
  font-size: 20px;
  cursor: pointer;
}

.chat-messages {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
}

.message {
  background: #444;
  padding: 10px;
  border-radius: 5px;
  margin-bottom: 10px;
}

.message.user {
  background: #2b3540;
  align-self: flex-end;
}

.message.bot {
  background: #555;
  align-self: flex-start;
}

.message.typing {
  background: #555;
  font-style: italic;
}

.typing .dot {
  animation: blink 1.4s infinite;
  animation-fill-mode: both;
}

.typing .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes blink {
  0% { opacity: 0.2; }
  20% { opacity: 1; }
  100% { opacity: 0.2; }
}

.chat-input {
  display: flex;
  padding: 15px;
  border-top: 1px solid #555;
  background: #222;
}

.chat-input input {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 5px;
  background: #555;
  color: white;
}

.chat-input button {
  background: #2b3540;
  color: white;
  border: none;
  padding: 10px;
  margin-left: 10px;
  cursor: pointer;
  border-radius: 5px;
}
</style>
