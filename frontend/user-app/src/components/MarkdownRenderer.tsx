import React from "react";
import { Info } from "lucide-react";

interface MarkdownRendererProps {
  content: string;
  onCitationClick?: (citationId: string) => void;
}

interface ListItem {
  text: string;
  subItems: string[];
}

interface Block {
  type: "heading" | "callout" | "table" | "list" | "paragraph";
  level?: number;
  text?: string;
  listItems?: ListItem[];
  headers?: string[];
  rows?: string[][];
}

export default function MarkdownRenderer({ content, onCitationClick }: MarkdownRendererProps) {
  // 1. Normalize text and clean up common LLM formatting glitches
  const cleanContent = (raw: string): string => {
    return raw
      .replace(/\r\n/g, "\n")
      // Remove trailing space before punctuation attached to citations: e.g. "[1] ." -> "[1]."
      .replace(/(\[\d+\])\s+([.,;:!?])/g, "$1$2")
      // Fix stray or asymmetric asterisks on labeled items like "*Breakfast:*" or "Breakfast:*" -> "**Breakfast:**"
      .replace(/(?:^|\s)\*([A-Za-z0-9\s/&'-]+):\*(?=\s)/gm, " **$1:**")
      .replace(/(?:^|\s)([A-Za-z0-9\s/&'-]+):\*(?=\s)/gm, " **$1:**");
  };

  const renderInline = (text: string) => {
    // Process citations [1], bold **text**, italic *text*, inline code `code`
    const parts: React.ReactNode[] = [];
    const regex = /(\[\d+\])|(\*\*[^*]+\*\*)|(\*[^*]+\*)|(`[^`]+`)/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
      }

      const matchedStr = match[0];

      if (matchedStr.startsWith("[") && matchedStr.endsWith("]")) {
        const num = matchedStr.slice(1, -1);
        parts.push(
          <button
            key={`cite-${match.index}`}
            type="button"
            className="citation-pill"
            title={`View Source Excerpt [${num}]`}
            onClick={() => onCitationClick && onCitationClick(num)}
          >
            [{num}]
          </button>
        );
      } else if (matchedStr.startsWith("**") && matchedStr.endsWith("**")) {
        parts.push(<strong key={`b-${match.index}`}>{matchedStr.slice(2, -2)}</strong>);
      } else if (matchedStr.startsWith("*") && matchedStr.endsWith("*")) {
        parts.push(<em key={`i-${match.index}`}>{matchedStr.slice(1, -1)}</em>);
      } else if (matchedStr.startsWith("`") && matchedStr.endsWith("`")) {
        parts.push(<code key={`c-${match.index}`} className="inline-code">{matchedStr.slice(1, -1)}</code>);
      }

      lastIndex = regex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }

    return parts;
  };

  // 2. Parse into structured blocks
  const parseBlocks = (raw: string): Block[] => {
    const lines = cleanContent(raw).split("\n");
    const blocks: Block[] = [];
    let currentList: ListItem[] | null = null;
    let currentParagraph: string[] = [];

    const flushParagraph = () => {
      if (currentParagraph.length > 0) {
        const text = currentParagraph.join(" ").trim();
        if (text) {
          // Check if this paragraph is a Note / Callout
          if (/^>\s*\**Note:?\**/i.test(text) || /^\(?Note\s*:/i.test(text)) {
            const cleanedNote = text
              .replace(/^>\s*/, "")
              .replace(/^\(?Note\s*:?\s*\)?/i, "")
              .replace(/\)$/, "")
              .trim();
            blocks.push({ type: "callout", text: cleanedNote });
          } else {
            blocks.push({ type: "paragraph", text });
          }
        }
        currentParagraph = [];
      }
    };

    const flushList = () => {
      if (currentList && currentList.length > 0) {
        blocks.push({ type: "list", listItems: currentList });
        currentList = null;
      }
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      // Empty line -> flush
      if (!trimmed) {
        flushParagraph();
        flushList();
        continue;
      }

      // Blockquote or Standalone Note line
      if (trimmed.startsWith(">") || /^\(?Note\s*:/i.test(trimmed)) {
        flushParagraph();
        flushList();
        const noteText = trimmed
          .replace(/^>\s*/, "")
          .replace(/^\(?Note\s*:?\s*\)?/i, "")
          .replace(/\)$/, "")
          .trim();
        blocks.push({ type: "callout", text: noteText });
        continue;
      }

      // Markdown Headings
      if (trimmed.startsWith("#")) {
        flushParagraph();
        flushList();
        const levelMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
        if (levelMatch) {
          blocks.push({
            type: "heading",
            level: levelMatch[1].length,
            text: levelMatch[2].trim(),
          });
          continue;
        }
      }

      // Check for List Items (supports -, *, +, •, ◦, 1., etc.)
      const isBullet = /^\s*([•\u2022\u25cf\u25cb\u2043\-*+]|\d+\.)\s+/.test(line);
      if (isBullet) {
        flushParagraph();
        const leadingSpaces = (line.match(/^(\s*)/) || ["", ""])[1].length;
        const cleanText = line.replace(/^\s*([•\u2022\u25cf\u25cb\u2043\-*+]|\d+\.)\s+/, "").trim();

        if (!currentList) {
          currentList = [];
        }

        // Sub-item if indented by 2+ spaces, or if parent ended with colon ":" and current item is a short timing/key
        const isSubItem = leadingSpaces >= 2 && currentList.length > 0;

        if (isSubItem) {
          currentList[currentList.length - 1].subItems.push(cleanText);
        } else {
          currentList.push({ text: cleanText, subItems: [] });
        }
        continue;
      }

      // If we are currently inside a list and hit an un-bulleted line with leading indent:
      if (currentList && currentList.length > 0 && /^\s{2,}/.test(line)) {
        currentList[currentList.length - 1].subItems.push(trimmed);
        continue;
      }

      // Otherwise regular text paragraph
      flushList();
      currentParagraph.push(trimmed);
    }

    flushParagraph();
    flushList();

    return blocks;
  };

  const blocks = parseBlocks(content);

  return (
    <div className="markdown-body">
      {blocks.map((b, idx) => {
        if (b.type === "heading") {
          if (b.level === 1) return <h2 key={idx} className="md-h2">{renderInline(b.text || "")}</h2>;
          if (b.level === 2) return <h3 key={idx} className="md-h3">{renderInline(b.text || "")}</h3>;
          return <h4 key={idx} className="md-h4">{renderInline(b.text || "")}</h4>;
        }

        if (b.type === "callout") {
          return (
            <div key={idx} className="md-callout-card">
              <div className="md-callout-icon-wrap">
                <Info size={15} className="md-callout-icon" />
              </div>
              <div className="md-callout-content">
                <span className="md-callout-label">Official Note</span>
                <p className="md-callout-body">{renderInline(b.text || "")}</p>
              </div>
            </div>
          );
        }

        if (b.type === "list" && b.listItems) {
          return (
            <ul key={idx} className="md-list">
              {b.listItems.map((item, itemIdx) => (
                <li key={itemIdx} className="md-list-item">
                  <div className="md-list-item-content">{renderInline(item.text)}</div>
                  {item.subItems.length > 0 && (
                    <ul className="md-sublist">
                      {item.subItems.map((sub, sIdx) => (
                        <li key={sIdx} className="md-sublist-item">
                          <span className="md-sublist-bullet" />
                          <div className="md-sublist-text">{renderInline(sub)}</div>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          );
        }

        return (
          <p key={idx} className="md-p">
            {renderInline(b.text || "")}
          </p>
        );
      })}
    </div>
  );
}
