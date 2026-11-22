import React from "react";

interface MarkdownRendererProps {
  content: string;
  onCitationClick?: (citationId: string) => void;
}

export default function MarkdownRenderer({ content, onCitationClick }: MarkdownRendererProps) {
  // Parse paragraphs and lines
  const paragraphs = content.split(/\n\n+/);

  const renderInline = (text: string) => {
    // Process citations [1], [2], bold **text**, italic *text*, inline code `code`
    const parts: React.ReactNode[] = [];
    // Regex matching [N] citations or bold **..** or italic *..* or `..`
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

  return (
    <div className="markdown-body">
      {paragraphs.map((p, idx) => {
        const trimmed = p.trim();
        if (!trimmed) return null;

        // Headings
        if (trimmed.startsWith("### ")) {
          return <h4 key={idx} className="md-h4">{renderInline(trimmed.slice(4))}</h4>;
        }
        if (trimmed.startsWith("## ")) {
          return <h3 key={idx} className="md-h3">{renderInline(trimmed.slice(3))}</h3>;
        }
        if (trimmed.startsWith("# ")) {
          return <h2 key={idx} className="md-h2">{renderInline(trimmed.slice(2))}</h2>;
        }

        // List items
        if (trimmed.startsWith("- ") || trimmed.startsWith("* ") || /^\d+\.\s/.test(trimmed)) {
          const lines = trimmed.split("\n");
          return (
            <ul key={idx} className="md-list">
              {lines.map((line, lIdx) => {
                const clean = line.replace(/^[-*]\s+|\d+\.\s+/, "");
                return <li key={lIdx}>{renderInline(clean)}</li>;
              })}
            </ul>
          );
        }

        return (
          <p key={idx} className="md-p">
            {renderInline(trimmed)}
          </p>
        );
      })}
    </div>
  );
}
