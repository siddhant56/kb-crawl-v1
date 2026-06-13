"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { uploadApi, extractError } from "@/lib/api";
import type { UploadCategory, UploadResult } from "@/lib/types";

const FALLBACK_CATEGORIES: UploadCategory[] = [
  "blog",
  "services",
  "hire-developers",
  "case-studies",
  "industries",
  "resources",
  "about",
  "company",
  "uploads",
];

const ACCEPTED = ".pdf,.docx,.txt,.md";
const MAX_MB = 50;

// ─── Result panel ─────────────────────────────────────────────────────────────
function SuccessPanel({ result, onReset }: { result: UploadResult; onReset: () => void }) {
  const { sanitization } = result;
  const hasRedactions = sanitization.redactions_total > 0;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center shrink-0">
          <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Document added to knowledge base</h2>
          <p className="text-sm text-gray-500 mt-0.5">{result.filename}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { label: "Category", value: result.category },
          { label: "Chunks indexed", value: result.chunks_added },
          { label: "Chunks replaced", value: result.chunks_replaced },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gray-50 rounded-xl px-4 py-3">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-sm font-semibold text-gray-900 mt-0.5">{value}</p>
          </div>
        ))}
      </div>

      {/* Sanitization report */}
      {hasRedactions ? (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
          <p className="text-sm font-medium text-amber-800 mb-2">
            Sensitive data scrubbed ({sanitization.redactions_total} items redacted)
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(sanitization.by_category).map(([cat, count]) => (
              <span
                key={cat}
                className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-medium"
              >
                {cat}: {count}
              </span>
            ))}
          </div>
          <p className="text-xs text-amber-700 mt-2">
            Redacted values replaced with [REDACTED:CATEGORY] placeholders.
          </p>
        </div>
      ) : (
        <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3">
          <p className="text-sm text-green-800">No sensitive data detected.</p>
        </div>
      )}

      <button
        onClick={onReset}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-4 rounded-lg text-sm transition-colors"
      >
        Upload another document
      </button>
    </div>
  );
}

// ─── Drop zone ────────────────────────────────────────────────────────────────
function DropZone({
  file,
  onFile,
}: {
  file: File | null;
  onFile: (f: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped) onFile(dropped);
    },
    [onFile]
  );

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`cursor-pointer rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
        dragging
          ? "border-blue-400 bg-blue-50"
          : file
          ? "border-green-300 bg-green-50"
          : "border-gray-300 hover:border-gray-400 bg-white"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }}
      />

      {file ? (
        <div className="space-y-1">
          <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center mx-auto">
            <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-900">{file.name}</p>
          <p className="text-xs text-gray-500">{formatSize(file.size)} · click to change</p>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center mx-auto">
            <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-700">
            Drag & drop or <span className="text-blue-600">browse</span>
          </p>
          <p className="text-xs text-gray-400">PDF, DOCX, TXT, MD · max {MAX_MB} MB</p>
        </div>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState<UploadCategory>("uploads");
  const [categories, setCategories] = useState<UploadCategory[]>(FALLBACK_CATEGORIES);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);

  useEffect(() => {
    uploadApi.categories()
      .then(({ ok, data }) => { if (ok && data.categories.length > 0) setCategories(data.categories); })
      .catch(() => {});
  }, []);

  const reset = () => {
    setFile(null);
    setCategory("uploads");
    setTitle("");
    setError(null);
    setResult(null);
  };

  const handleFile = (f: File) => {
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`File is too large (${(f.size / 1024 / 1024).toFixed(1)} MB). Maximum is ${MAX_MB} MB.`);
      return;
    }
    setFile(f);
    setError(null);
    // Pre-fill title from filename stem
    if (!title) {
      const stem = f.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ");
      setTitle(stem.charAt(0).toUpperCase() + stem.slice(1));
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) { setError("Please select a file."); return; }

    setError(null);
    setLoading(true);
    const { ok, data } = await uploadApi.upload(file, category, title || undefined);
    setLoading(false);

    if (!ok) {
      setError(extractError(data));
      return;
    }

    setResult(data);
  };

  if (result) return (
    <div className="max-w-xl mx-auto px-4 py-10">
      <SuccessPanel result={result} onReset={reset} />
    </div>
  );

  return (
    <div className="max-w-xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Upload Document</h1>
        <p className="text-gray-500 text-sm mt-1">
          Add a PDF, Word doc, text, or Markdown file to the company knowledge base.
          Sensitive data (API keys, pricing, PII) is automatically scrubbed before indexing.
        </p>
      </div>

      <form onSubmit={submit} className="space-y-5">
        {/* Drop zone */}
        <DropZone file={file} onFile={handleFile} />

        {/* Category */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Category
          </label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as UploadCategory)}
            className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
          >
            {categories.map((c) => (
              <option key={c} value={c}>
                {c.charAt(0).toUpperCase() + c.slice(1).replace(/-/g, " ")}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-400 mt-1">
            Choose the category that best describes the document content.
          </p>
        </div>

        {/* Optional title */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Title <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Defaults to filename"
            className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
          />
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-start justify-between gap-3">
            <span className="text-sm text-red-700">{error}</span>
            <button type="button" onClick={() => setError(null)} className="text-red-400 hover:text-red-600 shrink-0">✕</button>
          </div>
        )}

        {/* Sanitization notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3">
          <p className="text-xs text-blue-700">
            <span className="font-medium">Privacy notice:</span> API keys, passwords, pricing data,
            email addresses, phone numbers, and client identifiers are automatically detected and
            replaced with [REDACTED] placeholders before indexing.
          </p>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !file}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white font-medium py-2.5 px-4 rounded-lg text-sm transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Processing &amp; indexing…
            </>
          ) : (
            "Upload to knowledge base"
          )}
        </button>

        {loading && (
          <p className="text-center text-xs text-gray-400">
            Converting, sanitizing, and embedding — this may take 10–30 seconds.
          </p>
        )}
      </form>
    </div>
  );
}
