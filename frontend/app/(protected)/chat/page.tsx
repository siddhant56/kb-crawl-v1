"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { chatApi, extractError } from "@/lib/api";
import type { ConversationMessage, Source } from "@/lib/types";

// ─── Helper: extract a readable filename from a server file path ─────────────
function parseSource(source: Source) {
  const parts = source.metadata.source.replace(/\\/g, "/").split("/");
  const filename = parts[parts.length - 1]?.replace(".md", "") ?? "source";
  const category = source.metadata.type ?? "document";
  const snippet =
    source.page_content.slice(0, 200) +
    (source.page_content.length > 200 ? "…" : "");
  return { filename, category, snippet };
}

// ─── Source accordion ─────────────────────────────────────────────────────────
function SourcesPanel({ sources }: { sources: Source[] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        <svg
          className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-90" : ""}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M7.293 4.293a1 1 0 011.414 0L13.414 9l-4.707 4.707a1 1 0 01-1.414-1.414L10.586 9 7.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
        {sources.length} source{sources.length !== 1 ? "s" : ""}
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {sources.map((s, i) => {
            const { filename, category, snippet } = parseSource(s);
            return (
              <div
                key={i}
                className="bg-gray-50 border border-gray-200 rounded-lg p-3"
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-xs font-semibold text-gray-700 capitalize">
                    {filename.replace(/-/g, " ")}
                  </span>
                  <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-medium capitalize">
                    {category}
                  </span>
                </div>
                <p className="text-xs text-gray-500 leading-relaxed">{snippet}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────
function MessageBubble({ msg }: { msg: ConversationMessage & { sources?: Source[] } }) {
  const isUser = msg.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%] bg-blue-600 text-white px-4 py-3 rounded-2xl rounded-br-sm text-sm leading-relaxed">
          {msg.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="flex gap-3 max-w-[80%]">
        {/* Avatar */}
        <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center shrink-0 mt-0.5">
          <span className="text-xs font-bold text-blue-700">R</span>
        </div>
        <div>
          <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-bl-sm text-sm leading-relaxed text-gray-800 shadow-sm">
            {/* Render newlines as line breaks */}
            {msg.content.split("\n").map((line, i) => (
              <span key={i}>
                {line}
                {i < msg.content.split("\n").length - 1 && <br />}
              </span>
            ))}
          </div>
          {"sources" in msg && msg.sources && (
            <SourcesPanel sources={msg.sources} />
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Typing indicator ─────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex gap-3">
        <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
          <span className="text-xs font-bold text-blue-700">R</span>
        </div>
        <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-bl-sm shadow-sm flex items-center gap-1.5">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
        </div>
      </div>
    </div>
  );
}

// ─── Welcome screen ───────────────────────────────────────────────────────────
function WelcomeScreen() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4">
      <div className="w-16 h-16 rounded-2xl bg-blue-600 flex items-center justify-center text-white text-2xl font-bold mb-6">
        C
      </div>
      <h2 className="text-xl font-semibold text-gray-900 mb-2">
        Company Expert Assistant
      </h2>
      <p className="text-gray-500 text-sm max-w-sm">
        Ask me anything about the company&apos;s services, team, projects, or
        expertise. I search the full knowledge base to give you accurate answers
        with sources.
      </p>
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-md">
        {[
          "What services does the company offer?",
          "How experienced is the team?",
          "Does the company do mobile development?",
          "What industries does the company serve?",
        ].map((q) => (
          <button
            key={q}
            className="text-left text-xs bg-white border border-gray-200 hover:border-blue-300 hover:bg-blue-50 px-4 py-3 rounded-xl text-gray-600 hover:text-gray-900 transition-all"
            onClick={() => {
              // Dispatch a custom event that the input listens to
              window.dispatchEvent(
                new CustomEvent("chat:suggest", { detail: q })
              );
            }}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Main chat page ───────────────────────────────────────────────────────────
export default function ChatPage() {
  const [messages, setMessages] = useState<
    (ConversationMessage & { sources?: Source[] })[]
  >([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Listen for suggested questions from the welcome screen
  useEffect(() => {
    const handler = (e: Event) => {
      const text = (e as CustomEvent<string>).detail;
      setInput(text);
      textareaRef.current?.focus();
    };
    window.addEventListener("chat:suggest", handler);
    return () => window.removeEventListener("chat:suggest", handler);
  }, []);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setError(null);

    // Snapshot history BEFORE adding the new user message
    const history = messages.map(({ role, content }) => ({ role, content }));

    // Optimistically add the user message
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    const { ok, data } = await chatApi.send(text, history);
    setLoading(false);

    if (!ok) {
      setError(extractError(data));
      return;
    }

    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: data.answer, sources: data.sources ?? [] },
    ]);
  }, [input, loading, messages]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setError(null);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Message area */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && !loading ? (
          <WelcomeScreen />
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-4 mb-2">
          <div className="max-w-3xl mx-auto bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-center justify-between">
            <span className="text-sm text-red-700">{error}</span>
            <button
              onClick={() => setError(null)}
              className="text-red-400 hover:text-red-600 ml-4 shrink-0"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Input bar */}
      <div className="border-t border-gray-200 bg-white px-4 py-4 shrink-0">
        <div className="max-w-3xl mx-auto flex gap-3 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything… (Enter to send, Shift+Enter for newline)"
            rows={1}
            disabled={loading}
            className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-400 transition max-h-40 overflow-y-auto leading-relaxed"
            style={{
              height: "auto",
              minHeight: "44px",
            }}
            onInput={(e) => {
              const el = e.currentTarget;
              el.style.height = "auto";
              el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
            }}
          />

          {messages.length > 0 && (
            <button
              onClick={clearChat}
              disabled={loading}
              title="Clear conversation"
              className="p-2.5 rounded-xl text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors disabled:opacity-50 shrink-0"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          )}

          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 disabled:cursor-not-allowed text-white disabled:text-gray-400 p-2.5 rounded-xl transition-colors shrink-0"
          >
            {loading ? (
              <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin block" />
            ) : (
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            )}
          </button>
        </div>

        <p className="text-center text-xs text-gray-400 mt-2">
          Answers are generated from the company knowledge base · Sources are
          shown below each response
        </p>
      </div>
    </div>
  );
}
