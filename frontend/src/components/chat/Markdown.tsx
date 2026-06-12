"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Check, Copy } from "lucide-react";

interface CodeBlockProps {
  language: string;
  value: string;
}

function CodeBlock({ language, value }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy code block:", err);
    }
  };

  return (
    <div className="relative my-4 rounded-lg border border-zinc-800/80 bg-zinc-950 overflow-hidden font-mono text-xs">
      <div className="flex items-center justify-between px-4 py-1.5 border-b border-zinc-800/60 bg-zinc-900/40 text-zinc-400 select-none">
        <span className="text-[10px] uppercase font-bold tracking-wider">{language || "code"}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-zinc-100 transition-colors p-1 rounded"
          title="Copy Code"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div className="p-4 overflow-x-auto text-zinc-300 leading-relaxed font-mono">
        <pre><code>{value}</code></pre>
      </div>
    </div>
  );
}

interface MarkdownProps {
  content: string;
}

export default function Markdown({ content }: MarkdownProps) {
  return (
    <div className="prose prose-invert max-w-none text-sm leading-relaxed text-zinc-300 space-y-3 prose-p:leading-relaxed prose-pre:p-0 prose-pre:bg-transparent prose-code:text-zinc-200">
      <ReactMarkdown
        components={{
          code({ node, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            const isInline = !match;
            const value = String(children).replace(/\n$/, "");

            if (isInline) {
              return (
                <code
                  className="bg-zinc-800/60 px-1.5 py-0.5 rounded text-zinc-200 border border-zinc-700/30 text-xs font-semibold"
                  {...props}
                >
                  {children}
                </code>
              );
            }

            return <CodeBlock language={match[1]} value={value} />;
          },
          p({ children }) {
            return <p className="mb-3 last:mb-0">{children}</p>;
          },
          ul({ children }) {
            return <ul className="list-disc pl-6 mb-3 space-y-1">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="list-decimal pl-6 mb-3 space-y-1">{children}</ol>;
          },
          h1({ children }) {
            return <h1 className="text-xl font-bold text-zinc-100 mt-6 mb-2 border-b border-zinc-800 pb-1">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="text-lg font-semibold text-zinc-100 mt-5 mb-2">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="text-base font-semibold text-zinc-200 mt-4 mb-1.5">{children}</h3>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-primary/50 pl-4 py-1 my-3 bg-zinc-900/30 text-zinc-400 rounded-r italic">
                {children}
              </blockquote>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
