"use client";

import {
  AlertTriangle,
  FileText,
  Library,
  RefreshCw,
  Search,
  Trash2,
  Upload,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Pagination } from "@/components/pagination";
import { DocumentStatusBadge } from "@/components/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatBytes, formatDateTime, relativeTime } from "@/lib/format";
import type { DocumentChunk, DocumentRecord } from "@/lib/types";
import { useAsyncData } from "@/lib/use-async";

const STATUSES = ["pending", "processing", "indexed", "failed"];
const PAGE_SIZE = 20;

export default function KnowledgePage() {
  const { me } = useAuth();
  const canManage = me?.role === "admin" || me?.role === "supervisor";

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string>("all");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [detail, setDetail] = useState<DocumentRecord | null>(null);
  const [deleting, setDeleting] = useState<DocumentRecord | null>(null);
  const [reindexing, setReindexing] = useState<DocumentRecord | null>(null);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    setOffset(0);
  }, [search, status]);

  const { data, loading, error, reload } = useAsyncData(
    () =>
      api.documents({
        search: search || undefined,
        status: status === "all" ? undefined : status,
        limit: PAGE_SIZE,
        offset,
      }),
    [search, status, offset],
  );

  const documents = data?.items ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Knowledge Base"
        title="Manuals & documents"
        description="Upload PDFs to ground the assistant. Documents are chunked, embedded and searched by organization."
        actions={
          canManage ? (
            <Button onClick={() => setUploadOpen(true)}>
              <Upload className="size-4" strokeWidth={1.5} />
              Upload PDF
            </Button>
          ) : undefined
        }
      />

      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-faint" strokeWidth={1.5} />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title or filename…"
            className="pl-11"
          />
        </div>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="sm:w-48">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {STATUSES.map((s) => (
              <SelectItem key={s} value={s} className="capitalize">
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-3xl" />
          ))}
        </div>
      ) : error ? (
        <EmptyState icon={AlertTriangle} title="Couldn't load documents" description={error} />
      ) : documents.length === 0 ? (
        <EmptyState
          icon={Library}
          title="No documents yet"
          description="Upload a PDF manual to give the assistant something to cite."
          action={
            canManage ? (
              <Button variant="secondary" onClick={() => setUploadOpen(true)}>
                <Upload className="size-4" strokeWidth={1.5} />
                Upload PDF
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <Card key={doc.id}>
              <CardContent className="flex items-center gap-4 p-5">
                <div className="flex size-11 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04]">
                  <FileText className="size-5 text-faint" strokeWidth={1.5} />
                </div>
                <button
                  className="min-w-0 flex-1 text-left"
                  onClick={() => setDetail(doc)}
                >
                  <p className="truncate text-sm font-medium">{doc.title}</p>
                  <p className="mt-0.5 truncate text-xs text-faint">
                    {doc.filename} · {formatBytes(doc.size_bytes)} ·{" "}
                    {doc.page_count} pages · {relativeTime(doc.created_at)}
                  </p>
                </button>
                <div className="hidden shrink-0 items-center gap-2 sm:flex">
                  <DocumentStatusBadge value={doc.status} />
                </div>
                {canManage ? (
                  <>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Reindex document"
                      onClick={() => setReindexing(doc)}
                      title="Reindex with a new file"
                    >
                      <RefreshCw className="size-4" strokeWidth={1.5} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Delete document"
                      onClick={() => setDeleting(doc)}
                      className="hover:text-danger"
                    >
                      <Trash2 className="size-4" strokeWidth={1.5} />
                    </Button>
                  </>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Pagination
        total={data?.total ?? 0}
        limit={PAGE_SIZE}
        offset={offset}
        onChange={setOffset}
      />

      <UploadDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onUploaded={() => void reload()}
      />
      <DetailDialog
        document={detail}
        onOpenChange={(open) => !open && setDetail(null)}
      />
      <DeleteDialog
        document={deleting}
        onOpenChange={(open) => !open && setDeleting(null)}
        onDeleted={() => void reload()}
      />
      <ReindexDialog
        document={reindexing}
        onOpenChange={(open) => !open && setReindexing(null)}
        onReindexed={() => void reload()}
      />
    </div>
  );
}

function UploadDialog({
  open,
  onOpenChange,
  onUploaded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUploaded: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) {
      setFile(null);
      setTitle("");
    }
  }, [open]);

  async function submit() {
    if (!file) {
      toast.error("Choose a PDF file first.");
      return;
    }
    setBusy(true);
    try {
      await api.uploadDocument(file, title || undefined);
      toast.success("Document indexed");
      onOpenChange(false);
      onUploaded();
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Upload failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload a document</DialogTitle>
          <DialogDescription>
            PDF only, up to 10 MB. It will be chunked and embedded for retrieval.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="doc-file">PDF file</Label>
            <input
              id="doc-file"
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full cursor-pointer rounded-2xl border border-white/10 bg-black/40 px-4 py-2.5 text-sm text-muted file:mr-3 file:rounded-full file:border-0 file:bg-white/10 file:px-3 file:py-1.5 file:text-xs file:text-foreground"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="doc-title">Title (optional)</Label>
            <Input
              id="doc-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Defaults to the filename"
            />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={() => void submit()} disabled={busy || !file}>
              {busy ? "Indexing…" : "Upload & index"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function DetailDialog({
  document,
  onOpenChange,
}: {
  document: DocumentRecord | null;
  onOpenChange: (open: boolean) => void;
}) {
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [loading, setLoading] = useState(false);
  const id = document?.id;

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const page = await api.documentChunks(id, { limit: 50 });
      setChunks(page.items);
    } catch {
      setChunks([]);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (document) void load();
    else setChunks([]);
  }, [document, load]);

  const totalTokens = useMemo(
    () => chunks.reduce((sum, c) => sum + c.token_count, 0),
    [chunks],
  );

  return (
    <Dialog open={Boolean(document)} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{document?.title}</DialogTitle>
          <DialogDescription>
            {document
              ? `${document.filename} · ${formatBytes(document.size_bytes)} · ${
                  document.page_count
                } pages`
              : ""}
          </DialogDescription>
        </DialogHeader>
        {document?.status === "failed" && document.error_message ? (
          <div className="mb-4 rounded-2xl border border-danger/25 bg-danger/[0.07] p-3 text-xs text-danger">
            {document.error_message}
          </div>
        ) : null}
        <div className="mb-4 flex flex-wrap gap-2 text-xs">
          <Badge tone="neutral">Indexed {formatDateTime(document?.indexed_at)}</Badge>
          <Badge tone="neutral">
            {chunks.length} chunks · {totalTokens.toLocaleString()} tokens
          </Badge>
        </div>
        <div className="max-h-[50vh] space-y-3 overflow-y-auto pr-1">
          {loading ? (
            <Skeleton className="h-24 rounded-2xl" />
          ) : chunks.length === 0 ? (
            <p className="py-6 text-center text-sm text-faint">
              No chunks available.
            </p>
          ) : (
            chunks.map((chunk) => (
              <div
                key={chunk.id}
                className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-3.5"
              >
                <div className="mb-1.5 flex items-center gap-2 text-[11px] text-faint">
                  <span className="font-mono">#{chunk.chunk_index}</span>
                  {chunk.page_number ? <span>p. {chunk.page_number}</span> : null}
                  <span className="ml-auto tabular-nums">
                    {chunk.token_count} tok
                  </span>
                  {chunk.has_embedding ? (
                    <Badge tone="success">embedded</Badge>
                  ) : (
                    <Badge tone="warning">no vector</Badge>
                  )}
                </div>
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-muted">
                  {chunk.content}
                </p>
              </div>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function DeleteDialog({
  document,
  onOpenChange,
  onDeleted,
}: {
  document: DocumentRecord | null;
  onOpenChange: (open: boolean) => void;
  onDeleted: () => void;
}) {
  const [busy, setBusy] = useState(false);
  async function confirm() {
    if (!document) return;
    setBusy(true);
    try {
      await api.deleteDocument(document.id);
      toast.success("Document removed");
      onOpenChange(false);
      onDeleted();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Delete failed.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog open={Boolean(document)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete document?</DialogTitle>
          <DialogDescription>
            “{document?.title}” and its embeddings will be permanently removed
            from this workspace.
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={() => void confirm()} disabled={busy}>
            {busy ? "Deleting…" : "Delete"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ReindexDialog({
  document,
  onOpenChange,
  onReindexed,
}: {
  document: DocumentRecord | null;
  onOpenChange: (open: boolean) => void;
  onReindexed: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!document) setFile(null);
  }, [document]);

  async function submit() {
    if (!file || !document) {
      toast.error("Choose a PDF file first.");
      return;
    }
    setBusy(true);
    try {
      await api.reindexDocument(document.id, file);
      toast.success("Document reindexed");
      onOpenChange(false);
      onReindexed();
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Reindex failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={Boolean(document)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reindex document</DialogTitle>
          <DialogDescription>
            Replace “{document?.title}” with a corrected PDF. Old chunks and
            embeddings are discarded and rebuilt from the new file.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="reindex-file">Replacement PDF</Label>
            <input
              id="reindex-file"
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full cursor-pointer rounded-2xl border border-white/10 bg-black/40 px-4 py-2.5 text-sm text-muted file:mr-3 file:rounded-full file:border-0 file:bg-white/10 file:px-3 file:py-1.5 file:text-xs file:text-foreground"
            />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={() => void submit()} disabled={busy || !file}>
              {busy ? "Reindexing…" : (
                <>
                  <RefreshCw className="size-4" strokeWidth={1.5} />
                  Reindex
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
