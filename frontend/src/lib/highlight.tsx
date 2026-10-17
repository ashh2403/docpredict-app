import type { ReactNode } from "react";

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Build a regex for a model feature. Bigrams may skip stop words that the model ignored ("payment is due"). */
export function termPattern(term: string): string {
  const parts = term
    .split(" ")
    .filter(Boolean)
    .map((p) => (p === "#" ? "\\d[\\d,.:/-]*" : escapeRegex(p)));
  return parts.join("\\W+(?:[A-Za-z']+\\W+){0,2}?");
}

/** Wrap occurrences of the given terms in <mark>. Longer terms take precedence. */
export function highlightTerms(text: string, terms: string[]): ReactNode[] {
  const usable = [...new Set(terms)].filter((t) => t.trim()).sort((a, b) => b.length - a.length);
  if (usable.length === 0) return [text];
  const re = new RegExp(`(?<![A-Za-z0-9])(${usable.map(termPattern).join("|")})(?![A-Za-z0-9])`, "gi");
  const out: ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = re.exec(text)) !== null) {
    if (match[0].length === 0) {
      re.lastIndex++;
      continue;
    }
    if (match.index > last) out.push(text.slice(last, match.index));
    out.push(<mark key={key++}>{match[0]}</mark>);
    last = match.index + match[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}
