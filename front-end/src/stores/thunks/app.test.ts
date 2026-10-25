import { vi } from "vitest";
import { setBackendVersion, setVersion } from "../slices/app";

const { mockGet, mockBackendGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockBackendGet: vi.fn(),
}));

vi.mock("axios", () => ({
  default: {
    create: vi.fn(({ baseURL }: { baseURL: string }) => ({
      get: baseURL === "/api" ? mockBackendGet : mockGet,
    })),
  },
}));

import { fetchAppVersion } from "./app";

describe("fetchAppVersion thunk", () => {
  const mockDispatch = vi.fn();
  const mockGetState = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: "2026.10.01", status: 200 });
    mockBackendGet.mockResolvedValue({ data: "2026.10.02", status: 200 });
  });

  const createThunkAPI = () => ({
    dispatch: mockDispatch,
    getState: mockGetState,
    extra: undefined,
    requestId: "test",
    signal: {
      aborted: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } as any,
    rejectWithValue: vi.fn(),
    fulfillWithValue: vi.fn(),
  });

  it("should dispatch setVersion on successful fetch", async () => {
    mockGet.mockResolvedValue({
      data: "2026.10.01",
      status: 200,
    });

    await fetchAppVersion()(mockDispatch, mockGetState, undefined);

    expect(mockGet).toHaveBeenCalledWith("/version");
    expect(mockDispatch).toHaveBeenCalledWith(setVersion("2026.10.01"));
    expect(mockBackendGet).toHaveBeenCalledWith("/version");
    expect(mockDispatch).toHaveBeenCalledWith(setBackendVersion("2026.10.02"));
  });

  it("should not dispatch setVersion on failed fetch", async () => {
    mockGet.mockRejectedValue(new Error("Network error"));

    await fetchAppVersion()(mockDispatch, mockGetState, undefined);

    expect(mockDispatch).not.toHaveBeenCalledWith(
      setVersion(expect.anything())
    );
    expect(mockDispatch).toHaveBeenCalledWith(setBackendVersion("2026.10.02"));
  });

  it("should not dispatch a version on non-200 status", async () => {
    mockGet.mockResolvedValue({
      data: "2026.10.01",
      status: 404,
    });
    mockBackendGet.mockResolvedValue({
      data: "2026.10.02",
      status: 404,
    });

    await fetchAppVersion()(mockDispatch, mockGetState, undefined);

    expect(mockDispatch).not.toHaveBeenCalledWith(
      setVersion(expect.anything())
    );
    expect(mockDispatch).not.toHaveBeenCalledWith(
      setBackendVersion(expect.anything())
    );
  });
});