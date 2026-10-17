import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api, ApiError, onUnauthorized, tokenStore } from "../lib/api";
import { passwordProblem, relativeTime, scoreBand, validateFile } from "../lib/format";
import { highlightTerms } from "../lib/highlight";
import { mockFetch } from "./fixtures";

describe("format helpers", () => {
  it("validates files on the client before upload", () => {
    expect(validateFile(new File(["x"], "a.pdf"))).toBeNull();
    expect(validateFile(new File(["x"], "A.DOCX"))).toBeNull();
    expect(validateFile(new File(["x"], "a.exe"))).toMatch(/Unsupported/);
    expect(validateFile(new File([], "a.txt"))).toMatch(/empty/);
    const big = new File(["x"], "big.pdf");
    Object.defineProperty(big, "size", { value: 11 * 1024 * 1024 });
    expect(validateFile(big)).toMatch(/larger than 10 MB/);
  });

  it("mirrors the server password policy", () => {
    expect(passwordProblem("short1")).toMatch(/8 characters/);
    expect(passwordProblem("onlyletters")).toMatch(/letter and one number/);
    expect(passwordProblem("Good1234")).toBeNull();
  });

  it("labels uncertain results as uncertain regardless of score", () => {
    expect(scoreBand(0.95, true)).toBe("Uncertain");
    expect(scoreBand(0.95, false)).toBe("Strong match");
    expect(scoreBand(0.55, false)).toBe("Moderate match");
  });

  it("formats relative times", () => {
    const now = new Date("2025-01-01T12:00:00Z");
    expect(relativeTime("2025-01-01T11:59:50Z", now)).toBe("just now");
    expect(relativeTime("2025-01-01T11:30:00Z", now)).toBe("30 min ago");
  });
});

describe("highlightTerms", () => {
  const marks = (text: string, terms: string[]) => {
    const { container } = render(<p>{highlightTerms(text, terms)}</p>);
    return Array.from(container.querySelectorAll("mark")).map((m) => m.textContent);
  };

  it("highlights unigrams case-insensitively on word boundaries", () => {
    expect(marks("Invoice total for the invoiced amount", ["invoice"])).toEqual(["Invoice"]);
  });

  it("matches bigrams across stop words the model ignored and number placeholders", () => {
    expect(marks("Payment is due within 14 days", ["payment", "# days"])).toEqual(["Payment", "14 days"]);
    expect(marks("The total amount due is listed", ["total amount"])).toEqual(["total amount"]);
  });

  it("escapes regex characters and returns plain text when nothing matches", () => {
    expect(marks("Cost (approx.) shown", ["(approx.)"])).toEqual(["(approx.)"]);
    expect(marks("abc and a.c", ["a.c"])).toEqual(["a.c"]); // "." is literal, so "abc" is not matched
    expect(marks("Nothing here", [])).toEqual([]);
  });
});

describe("api client", () => {
  it("sends the bearer token and parses JSON", async () => {
    tokenStore.set("tok-123");
    const { calls } = mockFetch({ "GET /api/users/me": { status: 200, body: { id: 1 } } });
    await expect(api.me()).resolves.toEqual({ id: 1 });
    expect(new Headers(calls[0].init?.headers).get("Authorization")).toBe("Bearer tok-123");
  });

  it("does not send a token to login and surfaces the server message", async () => {
    tokenStore.set("old");
    const { calls } = mockFetch({ "POST /api/auth/login": { status: 401, body: { detail: "Incorrect email or password." } } });
    const err = await api.login("a@b.co", "x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe("Incorrect email or password.");
    expect(new Headers(calls[0].init?.headers).get("Authorization")).toBeNull();
    expect(tokenStore.get()).toBe("old"); // a failed login does not end an existing session
  });

  it("clears the session and notifies listeners on 401", async () => {
    tokenStore.set("expired");
    mockFetch({ "GET /api/analyses": { status: 401, body: { detail: "Session expired." } } });
    const listener = vi.fn();
    const off = onUnauthorized(listener);
    await expect(api.listAnalyses()).rejects.toMatchObject({ status: 401 });
    expect(listener).toHaveBeenCalledOnce();
    expect(tokenStore.get()).toBeNull();
    off();
  });

  it("builds history query strings without empty values", async () => {
    tokenStore.set("t");
    const { calls } = mockFetch({ "GET /api/analyses": { status: 200, body: { items: [], total: 0, page: 1, page_size: 10 } } });
    await api.listAnalyses({ q: "acme", category: "", bookmarked: true, page: 2 });
    expect(calls[0].url).toBe("/api/analyses?q=acme&bookmarked=true&page=2");
  });

  it("reports a friendly message when the server is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(api.login("a@b.co", "x")).rejects.toMatchObject({ status: 0, message: expect.stringMatching(/Cannot reach/) });
  });
});
