"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { uploadApi, extractError } from "@/lib/api";
import type { UploadCategory, UploadHistoryItem, UploadResult } from "@/lib/types";

const FALLBACK_CATEGORIES: UploadCategory[] = [
  "blog", "services", "hire-developers", "case-studies",
  "industries", "resources", "about", "company", "uploads",
];

const ACCEPTED = ".pdf,.docx,.txt,.md";
const MAX_MB = 50;
const NEW_CATEGORY_SENTINEL = "__new__";
const CATEGORY_RE = /^[a-z][a-z0-9-]{0,49}$/;

type Tab = "upload" | "docs";

// ─── Success panel ────────────────────────────────────────────────────────────
function SuccessPanel({ result, onReset }: { result: UploadResult; onReset: () => void }) {
  const { sanitization } = result;
  const hasRedactions = sanitization.redactions_total > 0;

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 space-y-6 shadow-xl shadow-black/30">
      <div className="flex items-start gap-4">
        <div className="w-11 h-11 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <h2 className="text-base font-semibold text-zinc-100">Document added to knowledge base</h2>
          <p className="text-sm text-zinc-500 mt-0.5">{result.filename}</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Category", value: result.category },
          { label: "Chunks indexed", value: result.chunks_added },
          { label: "Chunks replaced", value: result.chunks_replaced },
        ].map(({ label, value }) => (
          <div key={label} className="bg-zinc-800/60 border border-zinc-700 rounded-xl px-4 py-3">
            <p className="text-xs text-zinc-500">{label}</p>
            <p className="text-sm font-semibold text-zinc-100 mt-0.5">{value}</p>
          </div>
        ))}
      </div>

      {hasRedactions ? (
        <div className="bg-amber-500/8 border border-amber-500/20 rounded-xl px-4 py-3">
          <p className="text-sm font-medium text-amber-400 mb-2">
            {sanitization.redactions_total} sensitive item{sanitization.redactions_total !== 1 ? "s" : ""} scrubbed
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(sanitization.by_category).map(([cat, count]) => (
              <span key={cat} className="text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded font-medium">
                {cat}: {count}
              </span>
            ))}
          </div>
          <p className="text-xs text-amber-500/70 mt-2">Replaced with [REDACTED:CATEGORY] placeholders.</p>
        </div>
      ) : (
        <div className="bg-emerald-500/8 border border-emerald-500/20 rounded-xl px-4 py-3">
          <p className="text-sm text-emerald-400">No sensitive data detected.</p>
        </div>
      )}

      <button
        onClick={onReset}
        className="w-full gradient-brand hover:opacity-90 text-white font-semibold py-2.5 px-4 rounded-lg text-sm transition-opacity"
      >
        Upload another document
      </button>
    </div>
  );
}

// ─── Drop zone ────────────────────────────────────────────────────────────────
function DropZone({ file, onFile }: { file: File | null; onFile: (f: File) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) onFile(dropped);
  }, [onFile]);

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
      className={`cursor-pointer rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-all ${
        dragging
          ? "border-indigo-500 bg-indigo-500/5"
          : file
          ? "border-emerald-500/50 bg-emerald-500/5"
          : "border-zinc-700 hover:border-zinc-600 bg-zinc-900 hover:bg-zinc-800/50"
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
        <div className="space-y-2">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto">
            <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-zinc-200">{file.name}</p>
          <p className="text-xs text-zinc-500">{formatSize(file.size)} · click to change</p>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="w-10 h-10 rounded-xl bg-zinc-800 border border-zinc-700 flex items-center justify-center mx-auto">
            <svg className="w-5 h-5 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <p className="text-sm font-medium text-zinc-300">
            Drag &amp; drop or <span className="text-indigo-400">browse</span>
          </p>
          <p className="text-xs text-zinc-600">PDF, DOCX, TXT, MD · max {MAX_MB} MB</p>
        </div>
      )}
    </div>
  );
}

// ─── My Documents table ───────────────────────────────────────────────────────
function DocsTab() {
  const [docs, setDocs] = useState<UploadHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    uploadApi.history().then(({ ok, data }) => {
      if (ok) setDocs(Array.isArray(data) ? data : []);
      else setError(extractError(data));
      setLoading(false);
    });
  }, []);

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <span className="w-6 h-6 border-2 border-zinc-700 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400">
        {error}
      </div>
    );
  }

  if (docs.length === 0) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl text-center py-16 text-zinc-600 text-sm">
        No documents uploaded yet.
      </div>
    );
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-zinc-800">
              {["File", "Category", "Chunks", "Uploaded by", "Date"].map((h) => (
                <th key={h} className="px-4 py-3 text-[11px] font-semibold text-zinc-600 uppercase tracking-wider">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {docs.map((doc) => (
              <tr key={doc.id} className="border-b border-zinc-800/60 hover:bg-zinc-800/30 transition-colors">
                <td className="px-4 py-3.5">
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0">
                      <svg className="w-3.5 h-3.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-zinc-200 truncate max-w-[200px]" title={doc.filename}>
                        {doc.filename}
                      </p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3.5">
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded border bg-zinc-800 text-zinc-400 border-zinc-700 capitalize">
                    {doc.category}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-sm text-zinc-400">{doc.chunks_added}</td>
                <td className="px-4 py-3.5 text-xs text-zinc-500 truncate max-w-[160px]">{doc.uploaded_by}</td>
                <td className="px-4 py-3.5 text-xs text-zinc-600 whitespace-nowrap">{formatDate(doc.uploaded_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-zinc-700 px-4 py-3 border-t border-zinc-800">
        {docs.length} document{docs.length !== 1 ? "s" : ""} in the knowledge base
      </p>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function UploadPage() {
  const [tab, setTab] = useState<Tab>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState<UploadCategory>("uploads");
  const [categories, setCategories] = useState<UploadCategory[]>(FALLBACK_CATEGORIES);
  const [newCategory, setNewCategory] = useState("");
  const [newCategoryError, setNewCategoryError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);

  const isAddingNew = category === NEW_CATEGORY_SENTINEL;
  const effectiveCategory = isAddingNew ? newCategory.trim() : category;

  useEffect(() => {
    uploadApi.categories()
      .then(({ ok, data }) => { if (ok && data.categories?.length > 0) setCategories(data.categories); })
      .catch(() => {});
  }, []);

  const reset = () => {
    setFile(null); setCategory("uploads"); setNewCategory("");
    setNewCategoryError(null); setTitle(""); setError(null); setResult(null);
  };

  const handleNewCategoryChange = (val: string) => {
    const slug = val.toLowerCase().replace(/\s+/g, "-");
    setNewCategory(slug);
    if (slug && !CATEGORY_RE.test(slug)) {
      setNewCategoryError("Only lowercase letters, digits, and hyphens. Must start with a letter.");
    } else {
      setNewCategoryError(null);
    }
  };

  const handleFile = (f: File) => {
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`File too large (${(f.size / 1024 / 1024).toFixed(1)} MB). Maximum is ${MAX_MB} MB.`);
      return;
    }
    setFile(f);
    setError(null);
    if (!title) {
      const stem = f.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ");
      setTitle(stem.charAt(0).toUpperCase() + stem.slice(1));
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) { setError("Please select a file."); return; }
    if (isAddingNew) {
      if (!effectiveCategory) { setNewCategoryError("Category name is required."); return; }
      if (!CATEGORY_RE.test(effectiveCategory)) {
        setNewCategoryError("Only lowercase letters, digits, and hyphens. Must start with a letter.");
        return;
      }
    }

    setError(null);
    setLoading(true);
    const { ok, data } = await uploadApi.upload(file, effectiveCategory, title || undefined);
    setLoading(false);

    if (!ok) { setError(extractError(data)); return; }
    setResult(data);
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-zinc-50 tracking-tight">Documents</h1>
        <p className="text-zinc-500 text-sm mt-1.5">
          Upload files to the knowledge base or browse previously indexed documents.
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-6 bg-zinc-900 border border-zinc-800 rounded-xl p-1 w-fit">
        {(["upload", "docs"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); if (t === "upload" && result) reset(); }}
            className={`text-sm px-4 py-1.5 rounded-lg font-medium transition-colors ${
              tab === t
                ? "gradient-brand text-white shadow-sm"
                : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
            }`}
          >
            {t === "upload" ? "Upload" : "My Documents"}
          </button>
        ))}
      </div>

      {/* Upload tab */}
      {tab === "upload" && (
        result ? (
          <SuccessPanel result={result} onReset={reset} />
        ) : (
          <form onSubmit={submit} className="space-y-5">
            <DropZone file={file} onFile={handleFile} />

            {/* Category */}
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1.5">Category</label>
              <select
                value={category}
                onChange={(e) => { setCategory(e.target.value as UploadCategory); setNewCategory(""); setNewCategoryError(null); }}
                className="w-full input-dark px-3.5 py-2.5 text-sm appearance-none"
              >
                {categories.map((c) => (
                  <option key={c} value={c} className="bg-zinc-900">
                    {c.charAt(0).toUpperCase() + c.slice(1).replace(/-/g, " ")}
                  </option>
                ))}
                <option value={NEW_CATEGORY_SENTINEL} className="bg-zinc-900">＋ Add new category…</option>
              </select>

              {isAddingNew && (
                <div className="mt-2">
                  <input
                    type="text"
                    autoFocus
                    value={newCategory}
                    onChange={(e) => handleNewCategoryChange(e.target.value)}
                    placeholder="e.g. quarterly-reports"
                    className={`w-full input-dark px-3.5 py-2.5 text-sm ${
                      newCategoryError ? "border-red-500/50 focus:ring-red-500/30 focus:border-red-500" : ""
                    }`}
                  />
                  {newCategoryError ? (
                    <p className="text-xs text-red-400 mt-1">{newCategoryError}</p>
                  ) : (
                    <p className="text-xs text-zinc-600 mt-1">
                      Lowercase letters, digits, and hyphens only (e.g. <code className="text-zinc-500">my-topic</code>). Saved for all users.
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Optional title */}
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1.5">
                Title <span className="text-zinc-600 font-normal">(optional)</span>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Defaults to filename"
                className="w-full input-dark px-3.5 py-2.5 text-sm"
              />
            </div>

            {/* Error */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 flex items-start justify-between gap-3">
                <span className="text-sm text-red-400">{error}</span>
                <button type="button" onClick={() => setError(null)} className="text-red-500 hover:text-red-300 shrink-0 text-sm">✕</button>
              </div>
            )}

            {/* Privacy notice */}
            <div className="bg-indigo-500/8 border border-indigo-500/20 rounded-xl px-4 py-3">
              <p className="text-xs text-indigo-400/80">
                <span className="font-medium text-indigo-400">Privacy notice:</span> API keys, passwords, pricing data,
                email addresses, phone numbers, and client identifiers are automatically detected and
                replaced with [REDACTED] placeholders before indexing.
              </p>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !file || !!newCategoryError || (isAddingNew && !newCategory)}
              className="w-full gradient-brand hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-2.5 px-4 rounded-lg text-sm transition-opacity flex items-center justify-center gap-2"
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
              <p className="text-center text-xs text-zinc-600">
                Converting, sanitizing, and embedding — this may take 10–30 seconds.
              </p>
            )}
          </form>
        )
      )}

      {/* My Documents tab */}
      {tab === "docs" && <DocsTab />}
    </div>
  );
}
