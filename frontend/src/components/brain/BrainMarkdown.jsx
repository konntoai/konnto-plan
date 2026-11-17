import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

const BLOCK = /^\s*([-*+]\s|\d+[.)]\s|\||#{1,6}\s|>)/;

/** Keep single line breaks from plain-text replies (briefs, older messages) without breaking lists or tables. */
function softBreaks(text) {
  const lines = (text || "").split("\n");
  return lines
    .map((line, i) => {
      const next = lines[i + 1];
      if (!line.trim() || next === undefined || !next.trim()) return line;
      if (line.trim().startsWith("|") || BLOCK.test(next) || /^#{1,6}\s/.test(line.trim())) return line;
      return `${line}  `;
    })
    .join("\n");
}

/** Source numbers like [3] become small chips that match the source list under the answer. */
const citeMarkers = (text) => text.replace(/\[(\d{1,2})\](?![(\[])/g, "[$1](#cite-$1)");

const components = {
  p: ({ node, ...p }) => <p className="mb-2.5 last:mb-0" {...p} />,
  ul: ({ node, ...p }) => <ul className="mb-2.5 last:mb-0 list-disc pl-5 space-y-1 marker:text-primary/70" {...p} />,
  ol: ({ node, ...p }) => <ol className="mb-2.5 last:mb-0 list-decimal pl-5 space-y-1 marker:text-primary/80 marker:font-semibold" {...p} />,
  li: ({ node, ...p }) => <li className="pl-0.5" {...p} />,
  h1: ({ node, ...p }) => <h3 className="font-display font-bold text-[16px] mt-4 mb-1.5 first:mt-0" {...p} />,
  h2: ({ node, ...p }) => <h3 className="font-display font-bold text-[16px] mt-4 mb-1.5 first:mt-0" {...p} />,
  h3: ({ node, ...p }) => <h3 className="font-display font-bold text-[15px] mt-4 mb-1.5 first:mt-0" {...p} />,
  h4: ({ node, ...p }) => <h4 className="font-semibold text-[14px] mt-3 mb-1 first:mt-0" {...p} />,
  strong: ({ node, ...p }) => <strong className="font-semibold text-foreground" {...p} />,
  a: ({ node, href, children, ...p }) => (href || "").startsWith("#cite-")
    ? <sup className="mx-0.5 inline-grid h-4 min-w-4 place-items-center rounded-full bg-primary/15 px-1 font-mono text-[10px] font-semibold text-primary align-super" data-testid="brain-cite-marker">{children}</sup>
    : <a className="text-primary underline underline-offset-2" target="_blank" rel="noreferrer" href={href} {...p}>{children}</a>,
  hr: () => <div className="my-3 h-px bg-border" />,
  blockquote: ({ node, ...p }) => <blockquote className="my-2 border-l-2 border-primary/40 pl-3 text-muted-foreground" {...p} />,
  code: ({ node, inline, ...p }) => <code className="rounded bg-[hsl(var(--surface-2))] px-1 py-0.5 font-mono text-[0.85em]" {...p} />,
  table: ({ node, ...p }) => (
    <div className="my-3 overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-[13px] border-collapse" {...p} />
    </div>
  ),
  thead: ({ node, ...p }) => <thead className="bg-[hsl(var(--surface-2))]" {...p} />,
  th: ({ node, ...p }) => <th className="px-3 py-2 text-left font-semibold border-b border-border whitespace-nowrap" {...p} />,
  td: ({ node, ...p }) => <td className="px-3 py-2 border-b border-border/60 align-top" {...p} />,
};

export function BrainMarkdown({ text, className = "" }) {
  return (
    <div className={cn("break-words", className)} data-testid="brain-markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{citeMarkers(softBreaks(text))}</ReactMarkdown>
    </div>
  );
}

export default BrainMarkdown;
