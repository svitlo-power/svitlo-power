import { createElement } from "react";
import { Provider } from "react-redux";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter } from "react-router-dom";
import { vi, beforeEach } from "vitest";
import { createTestStore } from "../../test/storeTestUtils";
import { MessageEditPage } from "./messageEdit";
import { MessageEdit } from "../../schemas";

// ResizeObserver is not a constructor in jsdom; mock it as a class
global.ResizeObserver = class {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
};

const mockPost = vi.hoisted(() => vi.fn());

vi.mock("../../stores/store", async () => {
  const { useDispatch, useSelector } =
    await vi.importActual<typeof import("react-redux")>("react-redux");
  return { useAppDispatch: useDispatch, useAppSelector: useSelector };
});

vi.mock("../../utils/apiClient", () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: [] }),
    post: mockPost,
  },
}));

vi.mock("../../hooks", async () => {
  const actual = await vi.importActual<typeof import("../../hooks")>(
    "../../hooks",
  );
  return {
    ...actual,
    useDebounce: (func: () => void) => func,
    useFormHandler: () => ({
      handleFormSubmit: (fn: (data: any) => void) => (e: any) => {
        e.preventDefault();
        fn({} as any);
      },
      hasFieldError: () => false,
      renderField: () => null,
      registerFormButtons: () => ({
        isDirty: false,
        isValid: true,
        isEdit: true,
        handleReset: () => {},
      }),
      control: {
        getValues: () => ({
          name: "Test message",
          stations: ["station-1"],
          templateMacros: "{% macro test() %}hi{% endmacro %}",
          shouldSendTemplate: "true",
          timeoutTemplate: "300",
          messageTemplate: "Hello {{ name }}",
          language: "en",
        }),
      } as any,
      trigger: () => Promise.resolve(true),
      getControlValue: () => "",
      isValid: true,
      handleReset: () => {},
      setControlValue: () => {},
      getFieldError: () => null,
      getFieldChanged: () => false,
      errors: {},
      register: () => ({}),
      setValidationErrors: () => {},
    }),
  };
});

vi.mock("../../providers", () => ({
  useHeaderContent: () => ({ setHeaderText: vi.fn() }),
  useLoading: () => ({ isLoading: false }),
}));

vi.mock("../../utils", async () => {
  const actual = await vi.importActual<typeof import("../../utils")>(
    "../../utils",
  );
  const translations: Record<string, string> = {
    "button.preview": "Preview",
    "button.refresh": "Refresh",
    "templates.message": "Message template",
    "templates.shouldSend": "Should send template",
    "templates.timeout": "Timeout template",
    "templates.macros": "Shared code",
    "columns.name": "Name",
    "columns.language": "Language",
    "columns.enabled": "Enabled",
    "columns.bot": "Bot",
    "columns.stations": "Stations",
    "columns.channel": "Channel",
    "preview.title": "Message '{{name}}' preview",
  };
  return {
    ...actual,
    usePageTranslation: () => (key: string) => translations[key] ?? key,
  };
});

vi.mock("./components", () => ({
  openMessagePreviewDialog: vi.fn(),
  TemplateEditor: ({ name }: { name: string }) =>
    createElement("div", { "data-testid": `template-editor-${name}` }),
  LivePreviewPanel: ({ onRefresh }: { onRefresh?: () => void }) =>
    createElement("div", { "data-testid": "live-preview-panel" }, [
      createElement("button", { onClick: onRefresh, "data-testid": "live-preview-refresh" }, "Refresh"),
    ]),
}));

const defaultMessage: MessageEdit = {
  id: "507f1f77bcf86cd799439011",
  name: "Test message",
  enabled: true,
  channelId: "channel-1",
  channelName: "Channel 1",
  templateMacros: "{% macro test() %}hi{% endmacro %}",
  messageTemplate: "Hello {{ name }}",
  shouldSendTemplate: "true",
  timeoutTemplate: "300",
  stations: ["station-1"],
  botId: "bot-1",
  language: "en",
};

const renderPage = (message = defaultMessage) => {
  const store = createTestStore({
    messages: {
      messages: [],
      editingMessage: message,
      loading: false,
      error: null,
      changed: false,
      loadingPreview: false,
      templatePreview: undefined,
      previewError: undefined,
    },
    bots: { bots: [], loading: false, error: null },
    stations: { items: [], loading: false, error: null },
  });

  render(
    <Provider store={store}>
      <MantineProvider>
        <MemoryRouter>
          <MessageEditPage isEdit />
        </MemoryRouter>
      </MantineProvider>
    </Provider>,
  );

  return store;
};

describe("MessageEditPage live preview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPost.mockImplementation((url: string) => {
      if (url === "/stations/stations") {
        return Promise.resolve({ data: [] });
      }
      return Promise.resolve({
        data: {
          success: true,
          message: "Hello World",
          shouldSend: true,
          timeout: 300,
          nextSendTime: "2026-01-01T00:00:00Z",
          data: {},
        },
      });
    });
  });

  it("renders template editors", () => {
    renderPage();

    expect(screen.getByTestId("template-editor-messageTemplate")).toBeInTheDocument();
    expect(screen.getByTestId("template-editor-shouldSendTemplate")).toBeInTheDocument();
    expect(screen.getByTestId("template-editor-timeoutTemplate")).toBeInTheDocument();
    expect(screen.getByTestId("template-editor-templateMacros")).toBeInTheDocument();
  });

  it("renders live preview panel", () => {
    renderPage();

    expect(screen.getByTestId("live-preview-panel")).toBeInTheDocument();
  });

  it("generates preview on load when editing and form is valid", async () => {
    renderPage();

    await waitFor(() => expect(mockPost).toHaveBeenCalled());
  });

  it("refreshes preview on manual refresh", async () => {
    renderPage();

    await waitFor(() => expect(mockPost).toHaveBeenCalled());
    mockPost.mockClear();

    fireEvent.click(screen.getByTestId("live-preview-refresh"));

    await waitFor(() => expect(mockPost).toHaveBeenCalled());
  });
});
