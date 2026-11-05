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
    expect(mockSubscribe).toHaveBeenCalledWith(callback);

    unmount();
    expect(mockSubscribe.mock.results[0].value).toHaveBeenCalledTimes(1);
  });
});
