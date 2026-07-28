import { useState, useRef, useEffect } from "react";
import { useHistory } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Bot,
  CalendarDays,
  Loader2,
  Send,
  Sparkles,
  TimerReset,
  Trash2,
  User,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { sendAgentQuestion } from "../services/aiService";
import { motion, AnimatePresence } from "motion/react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  status?: "normal" | "error";
  provider?: string | null;
  model?: string | null;
  fallbackUsed?: boolean;
  llmError?: string | null;
}

const quickQuestions = [
  {
    icon: Activity,
    text: "Me dê um resumo dos eventos dos sensores nesta semana.",
    tone: "cyan",
  },
  {
    icon: AlertTriangle,
    text: "Quantas vezes a caixa ficou vazia nos últimos 20 dias?",
    tone: "amber",
  },
  {
    icon: CalendarDays,
    text: "Quantas vezes a caixa ficou cheia nesse mês?",
    tone: "blue",
  },
  {
    icon: TimerReset,
    text: "Quanto tempo a caixa ficou vazia neste mês?",
    tone: "green",
  },
];

export function ChatPage() {
  const history = useHistory();

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content:
        "Olá! Sou o assistente do AquaMonitor. Posso te ajudar a analisar os eventos do reservatório, como quantas vezes a caixa ficou vazia, cheia, tempo de funcionamento e resumos por período.",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  useEffect(() => {
    autoGrow();
  }, [inputValue]);

  function autoGrow() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const max = 160;
    el.style.height = Math.min(el.scrollHeight, max) + "px";
    el.style.overflowY = el.scrollHeight > max ? "auto" : "hidden";
  }

  function handleComposerKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSendMessage();
    }
  }

  const handleSendMessage = async (forcedQuestion?: string) => {
    const question = (forcedQuestion ?? inputValue).trim();
    if (!question || isTyping) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: question,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsTyping(true);

    try {
      const res = await sendAgentQuestion(userMessage.content, sessionId);
      if (res.session_id) {
        setSessionId(res.session_id);
      }

      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer,
        timestamp: new Date(),
        provider: res.provider,
        model: res.model,
        fallbackUsed: res.fallback_used,
        llmError: res.llm_error,
      };

      setMessages((prev) => [...prev, aiResponse]);
    } catch (err) {
      console.error(err);
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          "Erro ao consultar o assistente. Verifique sua conexão ou tente novamente em instantes.",
        timestamp: new Date(),
        status: "error",
      };
      setMessages((prev) => [...prev, aiResponse]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleQuickQuestion = (question: string) => {
    void handleSendMessage(question);
  };

  const handleClearChat = () => {
    if (confirm("Deseja limpar todo o histórico de conversa?")) {
      setMessages([
        {
          id: "1",
          role: "assistant",
          content:
            "Olá! Sou o assistente do AquaMonitor. Posso te ajudar a analisar os eventos do reservatório, como quantas vezes a caixa ficou vazia, cheia, tempo de funcionamento e resumos por período.",
          timestamp: new Date(),
        },
      ]);
      setSessionId(null);
    }
  };

  return (
    <div className="chat-shell">
      <header className="chat-header">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => history.push("/home")}
          className="chat-icon-button"
          title="Voltar"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="chat-title-block">
          <div className="chat-title-row">
            <div className="chat-title-icon">
              <Sparkles className="w-4 h-4" />
            </div>
            <h2>Assistente IA</h2>
          </div>
          <p>Online · conectado ao AquaMonitor</p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleClearChat}
          className="chat-icon-button"
          title="Limpar conversa"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </header>

      {messages.length <= 1 && (
        <section className="chat-quick-panel">
          <div className="chat-quick-heading">
            <Sparkles className="w-4 h-4" />
            <span>Perguntas rápidas</span>
          </div>
          <div className="chat-quick-grid">
            {quickQuestions.map((question) => {
              const Icon = question.icon;
              return (
                <button
                  key={question.text}
                  type="button"
                  className={`chat-quick-button chat-quick-${question.tone}`}
                  onClick={() => handleQuickQuestion(question.text)}
                  disabled={isTyping}
                >
                  <span className="chat-quick-icon">
                    <Icon className="w-4 h-4" />
                  </span>
                  <span>{question.text}</span>
                </button>
              );
            })}
          </div>
        </section>
      )}

      <section className="chat-messages" aria-live="polite">
        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className={`chat-message-row ${
                message.role === "user" ? "chat-message-row-user" : ""
              }`}
            >
              <div
                className={`chat-avatar ${
                  message.role === "user" ? "chat-avatar-user" : "chat-avatar-bot"
                }`}
              >
                {message.role === "user" ? (
                  <User className="w-4 h-4" />
                ) : (
                  <Bot className="w-4 h-4" />
                )}
              </div>

              <div
                className={`chat-bubble ${
                  message.role === "user" ? "chat-bubble-user" : "chat-bubble-bot"
                } ${message.status === "error" ? "chat-bubble-error" : ""}`}
              >
                <p>{message.content}</p>
                <time>
                  {message.timestamp.toLocaleTimeString("pt-BR", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </time>
                {message.role === "assistant" && (message.provider || message.model || message.fallbackUsed) && (
                  <span className="chat-bubble-meta">
                    {message.fallbackUsed ? "fallback deterministico" : [message.provider, message.model].filter(Boolean).join(" · ")}
                  </span>
                )}
                {message.llmError && (
                  <span className="chat-bubble-warning">{message.llmError}</span>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {isTyping && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="chat-message-row"
          >
            <div className="chat-avatar chat-avatar-bot">
              <Bot className="w-4 h-4" />
            </div>
            <div className="chat-typing">
              <Loader2 className="w-4 h-4" />
              <span>Analisando dados...</span>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </section>

      <footer className="chat-composer">
        <textarea
          ref={textareaRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleComposerKeyDown}
          placeholder="Digite sua pergunta..."
          rows={1}
          disabled={isTyping}
          aria-label="Campo de mensagem"
        />

        <Button
          onClick={() => void handleSendMessage()}
          disabled={!inputValue.trim() || isTyping}
          className="chat-send-button"
          title="Enviar pergunta"
        >
          <Send className="w-4 h-4" />
        </Button>
      </footer>
    </div>
  );
}
