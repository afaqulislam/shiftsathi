"use client";

import {
  AlertCircle,
  ArrowUp,
  BookOpen,
  History,
  MessageSquarePlus,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import type { Citation, Conversation, ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Turn {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  insufficient?: boolean;
}

export default function AssistantPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(async () => {
    try {
      const { items } = await api.conversations();
      setConversations(items);
    } catch {
      /* non-fatal */
    }
  }, []);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns, asking]);

  const openConversation = useCallback(async (id: string) => {
    setLoadingHistory(true);
    setConversationId(id);
    try {
      const detail = await api.conversation(id);
      setTurns(
        detail.messages.map((message: ChatMessage) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          citations: message.citations ?? undefined,
        })),
      );
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not load chat.");
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  const startNew = useCallback(() => {
    setConversationId(null);
    setTurns([]);
  }, []);

  async function ask() {
    const trimmed = question.trim();
    if (trimmed.length < 2 || asking) return;
    setQuestion("");
    const userTurn: Turn = {
      id: `u-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    setTurns((prev) => [...prev, userTurn]);
    setAsking(true);
    try {
      const res = await api.ask(trimmed, conversationId);
      setConversationId(res.conversation_id);
      setTurns((prev) => [
        ...prev,
        {
          id: res.message_id,
          role: "assistant",
          content: res.answer,
          citations: res.citations,
          insufficient: res.insufficient_evidence,
        },
      ]);
      void loadConversations();
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "The assistant failed to respond.",
      );
      setTurns((prev) => prev.filter((t) => t.id !== userTurn.id));
      setQuestion(trimmed);
    } finally {
      setAsking(false);
    }
  }

  async function removeConversation(id: string) {
    try {
      await api.deleteConversation(id);
      if (id === conversationId) startNew();
      await loadConversations();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Delete failed.");
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="AI Assistant"
        title="Ask your plant"
        description="Grounded answers from indexed manuals and verified resolution history — with citations, or an honest abstain."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              className="lg:hidden"
              onClick={() => setHistoryOpen(true)}
            >
              <History className="size-4" strokeWidth={1.5} />
              History
            </Button>
            <Button variant="secondary" onClick={startNew}>
              <MessageSquarePlus className="size-4" strokeWidth={1.5} />
              New chat
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
        <Card className="hidden h-[calc(100dvh-15rem)] lg:block">
          <CardContent className="flex h-full flex-col p-4">
            <p className="px-2 pb-3 text-[11px] font-medium uppercase tracking-[0.16em] text-muted">
              Conversations
            </p>
            <div className="flex-1 space-y-1 overflow-y-auto">
              <ConversationList
                conversations={conversations}
                conversationId={conversationId}
                onOpen={(id) => void openConversation(id)}
                onDelete={(id) => void removeConversation(id)}
                emptyClassName="px-2 py-6 text-center text-xs text-faint"
              />
            </div>
          </CardContent>
        </Card>

        <Card className="flex h-[calc(100dvh-15rem)] flex-col">
          <CardContent className="flex h-full flex-col p-0">
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-6">
              {loadingHistory ? (
                <div className="space-y-4">
                  <Skeleton className="h-16 rounded-2xl" />
                  <Skeleton className="h-24 rounded-2xl" />
                </div>
              ) : turns.length === 0 ? (
                <EmptyState
                  icon={Sparkles}
                  title="Ask a grounded question"
                  description="Try: “Spindle thermal protection error code kaise check karein?” Answers are cited to your documents."
                  className="mt-8"
                />
              ) : (
                <div className="space-y-5">
                  {turns.map((turn) =>
                    turn.role === "user" ? (
                      <div key={turn.id} className="flex justify-end">
                        <div className="max-w-[85%] rounded-3xl rounded-br-lg rounded-tr-lg border border-white/10 bg-white/[0.05] px-4 py-3 text-sm">
                          {turn.content}
                        </div>
                      </div>
                    ) : (
                      <div key={turn.id} className="flex flex-col gap-3">
                        <div className="max-w-[92%] rounded-3xl rounded-bl-lg border border-white/[0.07] bg-black/40 px-4 py-3.5 text-sm leading-relaxed">
                          <div className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-faint">
                            <Sparkles className="size-3.5 text-accent" strokeWidth={1.5} />
                            ShiftSathi
                          </div>
                          <p className="whitespace-pre-wrap text-foreground/90">
                            {turn.content}
                          </p>
                        </div>
                        {turn.insufficient ? (
                          <div className="flex items-start gap-2 rounded-2xl border border-warning/25 bg-warning/[0.07] px-3.5 py-2.5 text-xs text-warning">
                            <AlertCircle className="mt-0.5 size-3.5 shrink-0" strokeWidth={1.5} />
                            Not enough evidence in your indexed documents to answer
                            confidently.
                          </div>
                        ) : null}
                        {turn.citations && turn.citations.length > 0 ? (
                          <div className="space-y-2">
                            <p className="text-[11px] uppercase tracking-[0.14em] text-faint">
                              Sources
                            </p>
                            {turn.citations.map((cite) => (
                              <CitationCard key={cite.index} citation={cite} />
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ),
                  )}
                  {asking ? (
                    <div className="flex items-center gap-2 text-xs text-faint">
                      <span className="relative flex size-2">
                        <span className="absolute inline-flex size-full animate-pulse-ring rounded-full bg-accent/60" />
                        <span className="relative inline-flex size-2 rounded-full bg-accent" />
                      </span>
                      Retrieving evidence…
                    </div>
                  ) : null}
                </div>
              )}
            </div>

            <div className="border-t border-white/[0.06] p-4">
              <div className="flex items-end gap-3">
                <Textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void ask();
                    }
                  }}
                  placeholder="Ask about a machine, error code or procedure…"
                  className="min-h-[52px] resize-none"
                  rows={1}
                />
                <Button
                  size="icon"
                  className="size-11 shrink-0"
                  aria-label="Send"
                  disabled={asking || question.trim().length < 2}
                  onClick={() => void ask()}
                >
                  <ArrowUp className="size-4" strokeWidth={2} />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Conversations</DialogTitle>
          </DialogHeader>
          <div className="max-h-[60vh] space-y-1 overflow-y-auto">
            <ConversationList
              conversations={conversations}
              conversationId={conversationId}
              onOpen={(id) => {
                setHistoryOpen(false);
                void openConversation(id);
              }}
              onDelete={(id) => void removeConversation(id)}
              emptyClassName="py-8 text-center text-xs text-faint"
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ConversationList({
  conversations,
  conversationId,
  onOpen,
  onDelete,
  emptyClassName,
}: {
  conversations: Conversation[];
  conversationId: string | null;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
  emptyClassName?: string;
}) {
  if (conversations.length === 0) {
    return <p className={emptyClassName}>No conversations yet.</p>;
  }
  return (
    <>
      {conversations.map((c) => (
        <div
          key={c.id}
          className={cn(
            "group flex items-center gap-2 rounded-2xl px-3 py-2.5 transition-colors",
            c.id === conversationId ? "bg-white/[0.07]" : "hover:bg-white/[0.04]",
          )}
        >
          <button
            onClick={() => onOpen(c.id)}
            className="min-w-0 flex-1 text-left"
          >
            <p className="truncate text-sm text-foreground">{c.title}</p>
            <p className="text-[11px] text-faint">
              {relativeTime(c.updated_at)}
            </p>
          </button>
          <button
            aria-label="Delete conversation"
            onClick={() => onDelete(c.id)}
            className="rounded-full p-1.5 text-faint opacity-0 transition-opacity hover:bg-white/10 hover:text-danger group-hover:opacity-100"
          >
            <Trash2 className="size-3.5" strokeWidth={1.5} />
          </button>
        </div>
      ))}
    </>
  );
}

function CitationCard({ citation }: { citation: Citation }) {
  return (
    <div className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-3.5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="accent">[{citation.index}]</Badge>
        <span className="text-xs font-medium text-foreground">
          {citation.document_title}
        </span>
        {citation.page_number ? (
          <span className="text-[11px] text-faint">
            p. {citation.page_number}
          </span>
        ) : null}
        <span className="ml-auto text-[11px] tabular-nums text-faint">
          {Math.round(citation.score * 100)}% match
        </span>
      </div>
      <p className="mt-2 flex items-start gap-2 text-xs leading-relaxed text-muted">
        <BookOpen className="mt-0.5 size-3.5 shrink-0 text-faint" strokeWidth={1.5} />
        {citation.snippet}
      </p>
    </div>
  );
}
