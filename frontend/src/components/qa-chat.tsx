"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Loader2, MessageCircleQuestion, User, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Msg = { role: "user" | "ai"; text: string; meta?: string };

const SUGGESTED = [
  "โครงการนี้มี red flag อะไรบ้าง",
  "บริษัทผ่านคุณสมบัติไหม ถ้ามีทุนจดทะเบียน 5 ล้าน",
  "ส่งภายในวันไหน เวลาเท่าไหร่",
  "หลักประกันสัญญากี่ % ของงบ",
];

export function QaChat({ pid }: { pid: string }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scroller.current?.scrollTo({
      top: scroller.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, busy]);

  const send = async (q: string) => {
    if (!q.trim() || busy) return;
    setBusy(true);
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    try {
      const res = await api.askTor(pid, q);
      setMessages((m) => [
        ...m,
        {
          role: "ai",
          text: res.answer,
          meta: `${res.model.split("/")[1] || res.model} · ${res.duration_sec}s`,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "ai", text: `เกิดข้อผิดพลาด: ${String(e)}`, meta: "error" },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-[520px] flex-col rounded-xl border border-border bg-card">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <MessageCircleQuestion className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium">ถาม AI เกี่ยวกับ TOR</span>
      </div>

      <div ref={scroller} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              ถามอะไรก็ได้เกี่ยวกับโครงการนี้ ลองคลิกคำถามเริ่มต้นด้านล่าง
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTED.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-border bg-background px-3 py-1.5 text-xs text-muted-foreground hover:border-primary hover:text-foreground"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <Bubble key={i} msg={m} />
        ))}
        {busy && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            กำลังคิด...
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex items-center gap-2 border-t border-border p-3"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="พิมพ์คำถามที่นี่..."
          disabled={busy}
        />
        <Button type="submit" size="icon" disabled={busy || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}

function Bubble({ msg }: { msg: Msg }) {
  const isAi = msg.role === "ai";
  return (
    <div className={`flex gap-2 ${isAi ? "" : "flex-row-reverse"}`}>
      <div
        className={`grid h-7 w-7 shrink-0 place-items-center rounded-full ${
          isAi ? "bg-primary/10 text-primary" : "bg-secondary text-secondary-foreground"
        }`}
      >
        {isAi ? <Sparkles className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
      </div>
      <div className={`max-w-[80%] ${isAi ? "" : "flex flex-col items-end"}`}>
        <div
          className={`whitespace-pre-wrap rounded-lg px-3 py-2 text-sm leading-relaxed ${
            isAi
              ? "border border-border bg-background text-foreground"
              : "bg-primary text-primary-foreground"
          }`}
        >
          {msg.text}
        </div>
        {msg.meta && (
          <div className="mt-1 text-[10px] text-muted-foreground">{msg.meta}</div>
        )}
      </div>
    </div>
  );
}
