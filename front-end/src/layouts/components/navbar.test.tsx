import { renderWithStore, screen, fireEvent } from "../../test/storeTestUtils.tsx";
import { Navbar } from "./navbar";
import { MemoryRouter } from "react-router-dom";
import { TFunction } from "i18next";
import { vi } from "vitest";

// Mock translation function - properly typed
const mockT: TFunction = (key: string) => key;

// Mock components
vi.mock("../../components", () => ({
  CountryFlag: () => <span data-testid="country-flag" />,
  LangPicker: () => <span data-testid="lang-picker" />,
  ThemePicker: () => <span data-testid="theme-picker" />,
  UserAvatar: () => <span data-testid="user-avatar" />,
}));

vi.mock("../../routes", () => ({
  RootRoutes: [
    { path: "/dashboard", name: "dashboard", icon: "home", skipForMenu: false },
    { path: "/buildings", name: "buildings", icon: "building", skipForMenu: false },
    { path: "/stations", name: "stations", icon: "bolt", skipForMenu: false },
    { path: "/settings", name: "settings", icon: "cog", skipForMenu: true },
  ],
  MenuItem: {} as any,
}));

vi.mock("@fortawesome/react-fontawesome", () => ({
  FontAwesomeIcon: ({ icon }: { icon: string }) => <span data-testid={`icon-${icon}`} />,
}));

// Mock the entire slices module with all required exports
vi.mock("../../stores/slices", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    appStarted: vi.fn(() => ({ type: "app/started" })),
    authReducer: (state: any = {}) => state,
    botsReducer: (state: any = {}) => state,
    chatsReducer: (state: any = {}) => state,
    messagesReducer: (state: any = {}) => state,
    stationsReducer: (state: any = {}) => state,
    stationsDataReducer: (state: any = {}) => state,
    buildingsReducer: (state: any = {}) => state,
    stationConnectionsReducer: (state: any = {}) => state,
    usersReducer: (state: any = {}) => state,
    extDataReducer: (state: any = {}) => state,
    dashboardConfigReducer: (state: any = {}) => state,
    visitCounterReducer: (state: any = {}) => state,
    outagesScheduleReducer: (state: any = {}) => state,
    powerLogsReducer: (state: any = {}) => state,
    buildingsSummaryReducer: (state: any = {}) => state,
    extDevicesReducer: (state: any = {}) => state,
    loginHistoryReducer: (state: any = {}) => state,
    appReducer: (state: any = {}) => state,
    logout: { type: "auth/logout" },
    lookupValuesReducer: (state: any = {}) => state,
  };
});

const renderNavbar = (props = {}) => {
  const defaultProps = {
    t: mockT,
    user: { userName: "testuser" },
    isNavbarCollapsed: false,
    toggleNavbar: vi.fn(),
    closeMenu: vi.fn(),
    onProfileClick: vi.fn(),
    onLogoutClick: vi.fn(),
    ...props,
  };

  return renderWithStore(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <Navbar {...defaultProps} />
    </MemoryRouter>
  );
};

describe("Navbar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders logo", () => {
    renderNavbar();
    expect(screen.getByAltText("Logo")).toBeInTheDocument();
  });

  it("renders app title when not collapsed", () => {
    renderNavbar({ isNavbarCollapsed: false });
    expect(screen.getByText("Svitlo Power monitoring tool")).toBeInTheDocument();
  });

  it("does not render app title when collapsed", () => {
    renderNavbar({ isNavbarCollapsed: true });
    expect(screen.queryByText("Svitlo Power monitoring tool")).not.toBeInTheDocument();
  });

  it("renders nav title with correct translation key", () => {
    renderNavbar({ isNavbarCollapsed: false });
    expect(screen.getByText("navFull")).toBeInTheDocument();
  });

  it("renders navShort when collapsed", () => {
    renderNavbar({ isNavbarCollapsed: true });
    expect(screen.getByText("navShort")).toBeInTheDocument();
  });

  it("renders navigation menu items", () => {
    renderNavbar({ isNavbarCollapsed: false });
    expect(screen.getByText("dashboard")).toBeInTheDocument();
    expect(screen.getByText("buildings")).toBeInTheDocument();
    expect(screen.getByText("stations")).toBeInTheDocument();
  });

  it("does not render skipped menu items", () => {
    renderNavbar({ isNavbarCollapsed: false });
    expect(screen.queryByText("settings")).not.toBeInTheDocument();
  });

  it("renders VersionDisplay component", () => {
    renderNavbar({ isNavbarCollapsed: false });
    expect(screen.getByTestId("navbar-version-label")).toBeInTheDocument();
  });

  it("calls onProfileClick when profile button clicked", () => {
    const onProfileClick = vi.fn();
    renderNavbar({ onProfileClick, isNavbarCollapsed: false });
    fireEvent.click(screen.getByText("profile.title"));
    expect(onProfileClick).toHaveBeenCalled();
  });

  it("calls onLogoutClick when logout button clicked", () => {
    const onLogoutClick = vi.fn();
    renderNavbar({ onLogoutClick, isNavbarCollapsed: false });
    fireEvent.click(screen.getByText("logOut"));
    expect(onLogoutClick).toHaveBeenCalled();
  });

  it("renders user avatar and username when user provided", () => {
    renderNavbar({ user: { userName: "john" }, isNavbarCollapsed: false });
    expect(screen.getByTestId("user-avatar")).toBeInTheDocument();
    expect(screen.getByText("john")).toBeInTheDocument();
  });

  // Skip responsive-dependent tests - they require viewport/media query matching
  // which does not work in jsdom
  it.skip("renders language picker and theme picker on desktop", () => {
    renderNavbar({ isNavbarCollapsed: false });
    expect(screen.getByTestId("lang-picker")).toBeInTheDocument();
    expect(screen.getByTestId("theme-picker")).toBeInTheDocument();
  });

  it("calls toggleNavbar when switch is clicked", () => {
    const toggleNavbar = vi.fn();
    renderNavbar({ toggleNavbar, isNavbarCollapsed: false });
    const switchElement = screen.getByRole("switch");
    fireEvent.click(switchElement);
    expect(toggleNavbar).toHaveBeenCalled();
  });
});