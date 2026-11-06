import { useEffect, useRef } from "react";
import { eventsService } from "../services";
import { EventItem } from "../types";

export function useSubscribeEvents(
  callback: (event: EventItem) => void,
  enabled = true,
) {
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;

    const unsubscribe = eventsService.subscribe((event) =>
      callbackRef.current(event),
    );

    return () => {
      unsubscribe();
    };
  }, [enabled]);
}

export function useSubscribeEvent<T extends EventItem["type"]>(
  type: T,
  handler: (event: EventItem & { type: T }) => void,
) {
  const handlerRef = useRef(handler);

  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEffect(() => {
    const listener = (event: EventItem) => {
      if (event.type === type) {
        handlerRef.current(event as EventItem & { type: T });
      }
    };

    const unsubscribe = eventsService.subscribe(listener);
    return unsubscribe;
  }, [type]);
}
