import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { vi, beforeEach } from "vitest";
import { LivePreviewPanel } from "./livePreviewPanel";
import { TemplatePreview } from "../../../stores/types";

// ResizeObserver is not a constructor in jsdom; mock it as a class
global.ResizeObserver = class {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
};

const defaultPreview: TemplatePreview = {
  shouldSend: true,
  timeout: 300,
  message: "Hello World",
  nextSendTime: "2026-01-01T00:00:00Z",
  data: {},
};

const translations: Record<string, string> = {
  "preview.title": "Message '{{name}}' preview",
  "livePreview.invalidForm": "Form is invalid. Fix the errors to see the preview.",
  "livePreview.error": "Preview error: {{error}}",
  "button.refresh": "Refresh",
};

const t = (key: string, opts?: any) => {
  let msg = translations[key] ?? key;
  if (opts?.name !== undefined) {
    msg = msg.replace("{{name}}", String(opts.name));
  }
  if (opts?.error !== undefined) {
    msg = msg.replace("{{error}}", String(opts.error));
  }
  return msg;
};

const renderPanel = (props: Partial<Parameters<typeof LivePreviewPanel>[0]> = {}) => {
  const onRefresh = vi.fn();
  render(
    <MantineProvider>
      <LivePreviewPanel
        name={props.name ?? "Test message"}
        preview={props.preview}
        loading={props.loading ?? false}
        error={props.error}
        isValid={props.isValid ?? true}
        onRefresh={onRefresh}
        t={t}
      />
    </MantineProvider>,
  );
  return onRefresh;
};

describe("LivePreviewPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows preview content when valid and not loading", () => {
    renderPanel({ preview: defaultPreview });

    expect(screen.getByText("Message 'Test message' preview")).toBeInTheDocument();
    expect(screen.getByText("Hello World")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refresh" })).toBeInTheDocument();
  });

  it("shows invalid form message when form is invalid", () => {
    renderPanel({ preview: defaultPreview, isValid: false });

    expect(
      screen.getByText("Form is invalid. Fix the errors to see the preview."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Hello World")).not.toBeInTheDocument();
  });

  it("shows error message when there is a preview error", () => {
    renderPanel({ preview: defaultPreview, error: "Template syntax error" });

    expect(
      screen.getByText("Preview error: Template syntax error"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Hello World")).not.toBeInTheDocument();
  });

  it("shows loading overlay when loading", () => {
    renderPanel({ preview: defaultPreview, loading: true });

    expect(screen.queryByText("Hello World")).not.toBeInTheDocument();
  });

  it("calls onRefresh when refresh button is clicked", async () => {
    const onRefresh = renderPanel({ preview: defaultPreview });

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Refresh" })).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    expect(onRefresh).toHaveBeenCalledTimes(1);
  });
});
