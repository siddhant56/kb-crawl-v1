"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { chatApi, extractError } from "@/lib/api";
import type { ConversationMessage, Source } from "@/lib/types";
import { Logo } from "@/components/Logo";

function parseSource(source: Source) {
  const parts = source.metadata.source.replace(/\\/g, "/").split("/");
  const filename = parts[parts.length - 1]?.replace(".md", "") ?? "source";
  const category = source.metadata.type ?? "document";
  return { filename, category };
}

// ─── Right-side source panel ──────────────────────────────────────────────────
function SourcePanel({ source, onClose }: { source: Source; onClose: () => void }) {
  const { filename, category } = parseSource(source);

  return (
    <div className="h-full flex flex-col bg-zinc-900 border-l border-zinc-800">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 shrink-0">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-zinc-100 truncate capitalize">
            {filename.replace(/-/g, " ")}
          </h3>
          <span className="text-[11px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-1.5 py-0.5 rounded font-medium capitalize">
            {category}
          </span>
        </div>
        <button
          onClick={onClose}
          className="ml-3 p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors shrink-0"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="prose prose-sm prose-invert max-w-none prose-p:my-2 prose-headings:my-3 prose-pre:bg-zinc-800 prose-pre:rounded-lg prose-code:text-violet-400 prose-code:before:content-none prose-code:after:content-none text-zinc-300">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {source.page_content}
          </ReactMarkdown>
        </div>
      </div>

      <div className="px-4 py-2 border-t border-zinc-800 shrink-0">
        <p className="text-xs text-zinc-600 truncate" title={source.metadata.source}>
          {source.metadata.source}
        </p>
      </div>
    </div>
  );
}

// ─── Source chips ─────────────────────────────────────────────────────────────
function SourcesPanel({ sources, onSourceClick }: { sources: Source[]; onSourceClick: (s: Source) => void }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
      >
        <svg
          className={`w-3 h-3 transition-transform ${open ? "rotate-90" : ""}`}
          fill="currentColor" viewBox="0 0 20 20"
        >
          <path fillRule="evenodd" d="M7.293 4.293a1 1 0 011.414 0L13.414 9l-4.707 4.707a1 1 0 01-1.414-1.414L10.586 9 7.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
        {sources.length} source{sources.length !== 1 ? "s" : ""}
      </button>

      {open && (
        <div className="mt-2 flex flex-wrap gap-2">
          {sources.map((s, i) => {
            const { filename, category } = parseSource(s);
            return (
              <button
                key={i}
                onClick={() => onSourceClick(s)}
                className="flex items-center gap-2 bg-zinc-800/60 hover:bg-zinc-700/60 border border-zinc-700 hover:border-indigo-500/40 rounded-lg px-3 py-2 text-left transition-all group"
              >
                <svg className="w-3.5 h-3.5 text-zinc-500 group-hover:text-indigo-400 shrink-0 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-zinc-400 group-hover:text-zinc-200 truncate capitalize transition-colors">
                    {filename.replace(/-/g, " ")}
                  </p>
                  <p className="text-[10px] text-zinc-600 capitalize">{category}</p>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────
function MessageBubble({ msg, onSourceClick }: { msg: ConversationMessage & { sources?: Source[] }; onSourceClick: (s: Source) => void }) {
  const isUser = msg.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%] gradient-brand text-white px-4 py-3 rounded-2xl rounded-br-sm text-sm leading-relaxed shadow-lg shadow-indigo-900/20">
          {msg.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="flex gap-3 max-w-[82%]">
        <div className="shrink-0 mt-0.5">
          <Logo size={28} />
        </div>
        <div>
          <div className="bg-zinc-900 border border-zinc-800 px-4 py-3 rounded-2xl rounded-bl-sm text-sm leading-relaxed text-zinc-200 shadow-sm prose prose-sm prose-invert max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-pre:bg-zinc-800 prose-pre:rounded-lg prose-code:text-violet-400 prose-code:before:content-none prose-code:after:content-none prose-a:text-indigo-400">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {msg.content}
            </ReactMarkdown>
          </div>
          {"sources" in msg && msg.sources && (
            <SourcesPanel sources={msg.sources} onSourceClick={onSourceClick} />
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
        <div className="shrink-0">
          <Logo size={28} />
        </div>
        <div className="bg-zinc-900 border border-zinc-800 px-4 py-3.5 rounded-2xl rounded-bl-sm shadow-sm flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
          <span className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
          <span className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" />
        </div>
      </div>
    </div>
  );
}

// ─── Welcome screen ───────────────────────────────────────────────────────────
const SUGGESTIONS = [
  "What services does the company offer?",
  "How experienced is the team?",
  "Does the company do mobile development?",
  "What industries does the company serve?",
];

function WelcomeScreen() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4">
      <div className="mb-6">
        <Logo size={56} />
      </div>
      <h2 className="text-xl font-semibold text-zinc-100 mb-2 tracking-tight">
        Company Expert Assistant
      </h2>
      <p className="text-zinc-500 text-sm max-w-sm leading-relaxed">
        Ask anything about the company&apos;s services, team, projects, or
        expertise. I search the full knowledge base to give you accurate
        answers with sources.
      </p>
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-md">
        {SUGGESTIONS.map((q) => (
          <button
            key={q}
            onClick={() => window.dispatchEvent(new CustomEvent("chat:suggest", { detail: q }))}
            className="text-left text-xs bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-indigo-500/30 px-4 py-3 rounded-xl text-zinc-400 hover:text-zinc-200 transition-all"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Compaction notice ────────────────────────────────────────────────────────
function CompactionDivider() {
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="flex-1 h-px bg-zinc-800" />
      <span className="text-[11px] text-zinc-600 font-medium px-2">
        · Context compacted · older turns summarised for the AI ·
      </span>
      <div className="flex-1 h-px bg-zinc-800" />
    </div>
  );
}

// ─── Main chat page ───────────────────────────────────────────────────────────
const COMPACTION_THRESHOLD = 30;

export default function ChatPage() {
  const [messages, setMessages] = useState<(ConversationMessage & { sources?: Source[] })[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSource, setActiveSource] = useState<Source | null>(null);
  const [compacted, setCompacted] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Restore saved conversation on mount
  useEffect(() => {
    chatApi.history().then(({ ok, data }) => {
      if (ok && data.messages?.length > 0) {
        const restored = data.messages.map((m: { role: string; content: string }) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
        }));
        setMessages(restored);
        if (restored.length >= COMPACTION_THRESHOLD) setCompacted(true);
      }
      setHistoryLoading(false);
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

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

    const history = messages.map(({ role, content }) => ({ role, content }));

    // Show compaction notice when history crosses the threshold
    if (history.length >= COMPACTION_THRESHOLD && !compacted) setCompacted(true);

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
  }, [input, loading, messages, compacted]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const clearChat = async () => {
    await chatApi.clearHistory();
    setMessages([]);
    setError(null);
    setActiveSource(null);
    setCompacted(false);
  };

  // Show skeleton while history is loading
  if (historyLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-zinc-950">
        <span className="w-6 h-6 border-2 border-zinc-700 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  // Find the turn index where compaction boundary sits (after the 20th-from-last message)
  const compactionBoundaryIndex = compacted && messages.length > 20
    ? messages.length - 20
    : -1;

  return (
    <div className="h-full flex bg-zinc-950">
      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 && !loading ? (
            <WelcomeScreen />
          ) : (
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
              {messages.map((msg, i) => (
                <div key={i}>
                  {i === compactionBoundaryIndex && <CompactionDivider />}
                  <MessageBubble msg={msg} onSourceClick={setActiveSource} />
                </div>
              ))}
              {loading && <TypingIndicator />}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Error banner */}
        {error && (
          <div className="mx-4 mb-2">
            <div className="max-w-3xl mx-auto bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 flex items-center justify-between">
              <span className="text-sm text-red-400">{error}</span>
              <button onClick={() => setError(null)} className="text-red-500 hover:text-red-300 ml-4 shrink-0 text-sm">✕</button>
            </div>
          </div>
        )}

        {/* Input bar */}
        <div className="border-t border-zinc-800 bg-zinc-900/80 backdrop-blur-sm px-4 py-4 shrink-0">
          <div className="max-w-3xl mx-auto flex gap-3 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything… (Enter to send, Shift+Enter for newline)"
              rows={1}
              disabled={loading}
              className="flex-1 resize-none input-dark px-4 py-3 text-sm max-h-40 overflow-y-auto leading-relaxed disabled:opacity-50"
              style={{ height: "auto", minHeight: "44px" }}
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
                className="p-2.5 rounded-xl text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors disabled:opacity-40 shrink-0"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}

            <button
              onClick={send}
              disabled={loading || !input.trim()}
              className="gradient-brand hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed p-2.5 rounded-xl transition-opacity shrink-0"
            >
              {loading ? (
                <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin block" />
              ) : (
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>

          <p className="text-center text-xs text-zinc-700 mt-2">
            Answers are generated from the company knowledge base · Click a source to view its content
          </p>
        </div>
      </div>

      {/* Source panel */}
      {activeSource && (
        <div className="w-[380px] shrink-0 h-full">
          <SourcePanel source={activeSource} onClose={() => setActiveSource(null)} />
        </div>
      )}
    </div>
  );
}
