import { useRef, useState } from "react";
import { Send, Paperclip, Mic, Square, Loader2, Image as ImgIcon, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useBrainChat, useVoiceRecorder } from "@/context/BrainChatContext";
import { cn } from "@/lib/utils";

/**
 * Composer shared by the Chat page (prefix "chat") and the floating K-BRAIN panel (prefix "kbrain").
 */
export function BrainComposer({ prefix = "chat", placeholder = "Ask K-BRAIN about your business…", compact = false, onFocus, onSent, autoFocus = false }) {
  const { send, sending, attachments, pendingUploads, uploadFile, removeAttachment } = useBrainChat();
  const { recording, secs, start, stop } = useVoiceRecorder(uploadFile);
  const [text, setText] = useState("");
  const fileInput = useRef(null);

  const narrow = typeof window !== "undefined" && window.innerWidth < 640;
  const hint = narrow && placeholder.length > 16 ? "Ask K-BRAIN…" : placeholder;
  const canSend = (text.trim().length > 0 || attachments.length > 0) && !sending && pendingUploads === 0;

  const submit = async () => {
    if (!canSend) return;
    const body = text;
    setText("");
    onSent?.();
    const ok = await send(body);
    if (!ok) setText(body);
  };

  const pick = async (e) => {
    for (const f of Array.from(e.target.files || [])) await uploadFile(f);
    if (fileInput.current) fileInput.current.value = "";
  };

  return (
    <div>
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 pb-2" data-testid={`${prefix}-attachments-strip`}>
          {attachments.map((a, i) => (
            <span key={i} className="inline-flex items-center gap-2 rounded-full glass px-3 py-1.5 text-xs">
              {a.type === "audio" ? <Mic className="h-3.5 w-3.5 text-primary" /> : a.type === "image" ? <ImgIcon className="h-3.5 w-3.5 text-primary" /> : <Paperclip className="h-3.5 w-3.5 text-primary" />}
              <span className="max-w-[180px] truncate">{a.filename || (a.type === "audio" ? "Voice note" : a.type === "image" ? a.description?.slice(0, 40) || "Photo" : "File")}</span>
              <button className="text-muted-foreground hover:text-foreground" aria-label="Remove" data-testid={`${prefix}-attachment-remove`} onClick={() => removeAttachment(i)}><X className="h-3.5 w-3.5" /></button>
            </span>
          ))}
        </div>
      )}
      <div className={cn(
        "glass-strong p-1.5 transition-[box-shadow,border-color] duration-200 focus-within:border-primary/50",
        compact ? "rounded-2xl focus-within:shadow-[0_0_0_3px_hsl(var(--primary)/0.12)]" : "rounded-[26px] shadow-[0_20px_60px_-24px_hsl(var(--glow-blue))] focus-within:shadow-[0_20px_60px_-18px_hsl(var(--glow-blue)),0_0_0_4px_hsl(var(--primary)/0.10)]",
        sending && "k-trail"
      )}>
        {recording ? (
          <div className="flex items-center gap-3 px-3 py-1.5 min-h-[44px]" data-testid={`${prefix}-recording-bar`}>
            <span className="rec-dot" />
            <span className="font-mono tabular font-semibold text-sm">{String(Math.floor(secs / 60)).padStart(2, "0")}:{String(secs % 60).padStart(2, "0")}</span>
            <span className="k-wave flex-1" aria-hidden>{Array.from({ length: 18 }).map((_, i) => <span key={i} style={{ animationDelay: `${(i % 6) * 0.12}s` }} />)}</span>
            <Button size="sm" variant="ghost" onClick={() => stop(true)} data-testid={`${prefix}-record-cancel`}>Cancel</Button>
            <Button size="sm" onClick={() => stop(false)} data-testid={`${prefix}-record-stop`} className="rounded-full"><Square className="h-4 w-4" /> Stop</Button>
          </div>
        ) : (
          <div className="flex items-end gap-1">
            <input ref={fileInput} type="file" onChange={pick} className="hidden" accept="image/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt" multiple data-testid={`${prefix}-file-input`} />
            <Button type="button" variant="ghost" size="icon" className="shrink-0 rounded-full" aria-label="Attach" data-testid={`${prefix}-attach-button`} onClick={() => fileInput.current?.click()} disabled={pendingUploads > 0}>
              {pendingUploads > 0 ? <Loader2 className="h-5 w-5 animate-spin" /> : <Paperclip className="h-5 w-5" />}
            </Button>
            <Textarea
              data-testid={`${prefix}-composer-textarea`}
              value={text}
              autoFocus={autoFocus}
              onFocus={onFocus}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit(); } }}
              placeholder={hint}
              rows={1}
              className={cn("resize-none max-h-[140px] flex-1 border-0 bg-transparent px-2 shadow-none hover:border-0 focus-visible:ring-0 focus-visible:border-0", compact ? "min-h-[40px] py-2 text-[14px]" : "min-h-[44px] py-2.5 text-[15px]")}
            />
            <Button type="button" variant="ghost" size="icon" className="shrink-0 rounded-full" aria-label="Record voice" data-testid={`${prefix}-mic-button`} onClick={start}><Mic className="h-5 w-5" /></Button>
            <Button type="button" size="icon" aria-label="Send" data-testid={`${prefix}-composer-send-button`} disabled={!canSend} onClick={submit} className="shrink-0 rounded-full">
              {sending ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
