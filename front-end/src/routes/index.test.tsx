import { ReactNode } from "react";
import { Provider } from "react-redux";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { createTestStore } from "../test/storeTestUtils";
import { updateAuthData } from "../stores/slices/auth";
import Routes from "./index";

vi.mock("../pages", () => {
  const page = (testId: string) => () => <div data-testid={testId} />;

  return {
    LoginPage: page("login-page"),
    HomePage: page("home-page"),
    BuildingsPage: page("buildings-page"),
    StationsPage: page("stations-page"),
    StationDetailsPage: page("station-details-page"),
    BotsPage: page("bots-page"),
    ChatsPage: page("chats-page"),
    MessagesPage: page("messages-page"),
    MessageEditPage: page("message-edit-page"),
    UsersPage: page("users-page"),
    ExtDataPage: page("external-data-page"),
    NotFoundPage: page("not-found-page"),
    ChangePasswordPage: page("change-password-page"),
    AppLandingPage: page("app-landing-page"),
    ExtDevicesPage: page("external-devices-page"),
    PrivacyPolicyPage: page("privacy-policy-page"),
    PushPage: page("push-page"),
    SystemSettingsPage: page("system-settings-page"),
  };
});

vi.mock("../layouts/anonymousLayout", () => ({
  AnonymousLayout: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("../layouts/publicLayout", () => ({
  PublicLayout: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("../layouts/authenticatedLayout", async () => {
  const { Outlet } = await import("react-router-dom");
  return {
    AuthenticatedLayout: () => <Outlet />,
  };
});

vi.mock("../providers", () => ({
  PageHeaderContentProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

describe("Routes public landing page", () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.replaceState({}, "", "/");
  });

  afterEach(() => {
    cleanup();
    delete globalThis.__SVITLO_CONFIG__;
  });

  const renderRoutes = (accessToken?: string) => {
    const store = createTestStore();
    if (accessToken) {
      store.dispatch(updateAuthData({
        authData: { accessToken, refreshToken: null },
        isRefresh: false,
      }));
    }

    return render(
      <Provider store={store}>
        <Routes />
      </Provider>,
    );
  };

  it("redirects unauthenticated visitors to login when the public page is disabled", async () => {
    globalThis.__SVITLO_CONFIG__ = { disablePublicFrontend: true };

    renderRoutes();

    expect(await screen.findByTestId("login-page")).toBeInTheDocument();
    expect(screen.queryByTestId("buildings-page")).not.toBeInTheDocument();
  });

  it("shows the admin home page to authenticated visitors when the public page is disabled", async () => {
    globalThis.__SVITLO_CONFIG__ = { disablePublicFrontend: true };

    renderRoutes("access-token");

    expect(await screen.findByTestId("home-page")).toBeInTheDocument();
  });

  it("keeps the public landing page when the flag is disabled", async () => {
    globalThis.__SVITLO_CONFIG__ = { disablePublicFrontend: false };

    renderRoutes();

    expect(await screen.findByTestId("buildings-page")).toBeInTheDocument();
  });
});
