import { act, renderHook } from "@testing-library/react";
import { vi } from "vitest";

const { mockSubscribe } = vi.hoisted(() => ({
  mockSubscribe: vi.fn(() => vi.fn()),
}));

vi.mock("../services", () => ({
  eventsService: {
    subscribe: mockSubscribe,
  },
}));

import { useSubscribeEvents } from "./useSubscribeEvents";

describe("useSubscribeEvents", () => {
  it("waits to subscribe until enabled", () => {
    const callback = vi.fn();
    const { rerender, unmount } = renderHook(
      ({ enabled }) => useSubscribeEvents(callback, enabled),
      { initialProps: { enabled: false } },
    );

    expect(mockSubscribe).not.toHaveBeenCalled();

    act(() => rerender({ enabled: true }));
    expect(mockSubscribe).toHaveBeenCalledWith(expect.any(Function));

    unmount();
    expect(mockSubscribe.mock.results[0].value).toHaveBeenCalledTimes(1);
  });

  it("keeps the subscription stable and invokes the latest callback", () => {
    const firstCallback = vi.fn();
    const latestCallback = vi.fn();
    const { rerender } = renderHook(
      ({ callback }) => useSubscribeEvents(callback),
      { initialProps: { callback: firstCallback } },
    );
    const listener = mockSubscribe.mock.calls[0][0];

    rerender({ callback: latestCallback });

    expect(mockSubscribe).toHaveBeenCalledTimes(1);
    act(() => listener({ type: "test", data: {}, private: false }));
    expect(firstCallback).not.toHaveBeenCalled();
    expect(latestCallback).toHaveBeenCalledTimes(1);
  });
});
