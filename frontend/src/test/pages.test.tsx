import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { configure } from "@testing-library/react";
import { describe, expect, it } from "vitest";

// Authenticated pages are lazy-loaded chunks; the first import in a cold test run can exceed 1 s.
configure({ asyncUtilTimeout: 8000 });
import { AppRoutes, Providers } from "../App";
import { tokenStore } from "../lib/api";
import { analysis, mockFetch, user } from "./fixtures";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Providers>
        <AppRoutes />
      </Providers>
    </MemoryRouter>,
  );
}

describe("authentication flow", () => {
  it("redirects anonymous users from protected pages to sign-in", async () => {
    mockFetch({});
    renderAt("/history");
    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
  });

  it("signs in and lands on the dashboard with live stats", async () => {
    const { calls } = mockFetch({
      "POST /api/auth/login": { status: 200, body: { access_token: "tok", token_type: "bearer", expires_in: 3600, user } },
      "GET /api/analyses/stats": {
        status: 200,
        body: { total: 0, bookmarked: 0, uncertain: 0, average_confidence: null, by_category: [], by_priority: { low: 0, medium: 0, high: 0 }, per_day: [] },
      },
      "GET /api/analyses": { status: 200, body: { items: [], total: 0, page: 1, page_size: 5 } },
    });
    renderAt("/login");
    await userEvent.type(screen.getByLabelText("Email"), "alice@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "Sup3rSecret1");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { name: /Good (morning|afternoon|evening), Alice/ })).toBeInTheDocument();
    expect(await screen.findByText("No analyses yet")).toBeInTheDocument();
    expect(tokenStore.get()).toBe("tok");
    const body = JSON.parse(String(calls[0].init?.body));
    expect(body).toEqual({ email: "alice@example.com", password: "Sup3rSecret1" });
  });

  it("shows the server error when sign-in fails", async () => {
    mockFetch({ "POST /api/auth/login": { status: 401, body: { detail: "Incorrect email or password." } } });
    renderAt("/login");
    await userEvent.type(screen.getByLabelText("Email"), "alice@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrongpass1");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password.");
  });

  it("validates registration passwords before calling the server", async () => {
    const { calls } = mockFetch({});
    renderAt("/register");
    await userEvent.type(screen.getByLabelText("Full name"), "Alice");
    await userEvent.type(screen.getByLabelText("Email"), "alice@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "Good1234");
    await userEvent.type(screen.getByLabelText("Confirm password"), "Good12345");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Passwords do not match.");
    expect(calls).toHaveLength(0);
  });

  it("logs out through the server and returns to sign-in", async () => {
    tokenStore.set("tok");
    const { calls } = mockFetch({
      "GET /api/users/me": { status: 200, body: user },
      "GET /api/analyses/stats": {
        status: 200,
        body: { total: 0, bookmarked: 0, uncertain: 0, average_confidence: null, by_category: [], by_priority: { low: 0, medium: 0, high: 0 }, per_day: [] },
      },
      "GET /api/analyses": { status: 200, body: { items: [], total: 0, page: 1, page_size: 5 } },
      "POST /api/auth/logout": { status: 200, body: { detail: "Signed out." } },
    });
    renderAt("/dashboard");
    await screen.findByText("No analyses yet");
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST" && c.url === "/api/auth/logout")).toBe(true);
    expect(tokenStore.get()).toBeNull();
  });
});

describe("result page", () => {
  it("presents uncertain results honestly with reasons and highlighted evidence", async () => {
    tokenStore.set("tok");
    mockFetch({
      "GET /api/users/me": { status: 200, body: user },
      "GET /api/analyses/7": { status: 200, body: analysis },
    });
    renderAt("/analyses/7");
    expect(await screen.findByText("Best guess (uncertain)")).toBeInTheDocument();
    expect(screen.getByText(/This result is uncertain/)).toBeInTheDocument();
    expect(screen.getByText("Top model score 44% is below the 50% threshold.")).toBeInTheDocument();
    const evidence = screen.getByText((_, el) => el?.tagName === "BLOCKQUOTE");
    expect(within(evidence).getByText("minutes").tagName).toBe("MARK");
    expect(screen.getByRole("img", { name: /Model score 44%, uncertain/ })).toBeInTheDocument();
    expect(screen.getByText(/Nothing here is legal, medical or financial advice/)).toBeInTheDocument();
  });

  it("toggles the bookmark through the API", async () => {
    tokenStore.set("tok");
    const { calls } = mockFetch({
      "GET /api/users/me": { status: 200, body: user },
      "GET /api/analyses/7": { status: 200, body: analysis },
      "PATCH /api/analyses/7": { status: 200, body: { ...analysis, bookmarked: true } },
    });
    renderAt("/analyses/7");
    await userEvent.click(await screen.findByRole("button", { name: "Bookmark" }));
    expect(await screen.findByRole("button", { name: "Bookmarked" })).toHaveAttribute("aria-pressed", "true");
    const patch = calls.find((c) => c.method === "PATCH");
    expect(JSON.parse(String(patch?.init?.body))).toEqual({ bookmarked: true });
  });

  it("shows not-found for another user's or a missing analysis", async () => {
    tokenStore.set("tok");
    mockFetch({
      "GET /api/users/me": { status: 200, body: user },
      "GET /api/analyses/99": { status: 404, body: { detail: "Analysis not found." } },
    });
    renderAt("/analyses/99");
    expect(await screen.findByText("Analysis not found")).toBeInTheDocument();
  });
});

describe("history page", () => {
  it("sends the search term to the API after typing", async () => {
    tokenStore.set("tok");
    const { calls } = mockFetch({
      "GET /api/users/me": { status: 200, body: user },
      "GET /api/analyses": (url) => ({
        status: 200,
        body: url.includes("q=apple") ? { items: [analysis], total: 1, page: 1, page_size: 10 } : { items: [], total: 0, page: 1, page_size: 10 },
      }),
    });
    renderAt("/history");
    expect(await screen.findByText("Your history is empty")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Search history"), "apple");
    await waitFor(() => expect(calls.some((c) => c.url.includes("q=apple"))).toBe(true));
    expect((await screen.findAllByText("recipe.txt")).length).toBeGreaterThan(0);
  });
});
