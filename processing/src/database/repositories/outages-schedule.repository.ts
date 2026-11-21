import { Inject, Injectable } from "@nestjs/common";
import { RedisClientType } from "redis";
import { SchedulesResponse, keepOnlyDefiniteSlots } from "../../shared.js";
import { REDIS_READER } from "../../tokens.js";

/** Redis hash holding one JSON `UnitSchedule` per queue. */
export const OUTAGES_SCHEDULE_REDIS_KEY = "outages_schedule";

/**
 * Reads the cached Yasno outage schedules.
 *
 * The legacy producer reads them from the Redis `outages_schedule` hash
 * (`RedisOutagesScheduleRepository`); this repository keeps the same source so
 * the shadow snapshot is comparable with production.
 */
@Injectable()
export class OutagesScheduleRepository {
  constructor(@Inject(REDIS_READER) private readonly redis: RedisClientType) {}

  async getSchedule(queue: string): Promise<SchedulesResponse> {
    const raw = await this.redis.hGet(OUTAGES_SCHEDULE_REDIS_KEY, queue);
    if (!raw) return {};
    try {
      return keepOnlyDefiniteSlots({
        [queue]: JSON.parse(raw),
      }) as SchedulesResponse;
    } catch {
      return {};
    }
  }

  /** All queues, with non-`Definite` slots removed like `SchedulesResponse`. */
  async getAllSchedules(): Promise<SchedulesResponse> {
    const data = await this.redis.hGetAll(OUTAGES_SCHEDULE_REDIS_KEY);
    const root: Record<string, unknown> = {};
    for (const [queue, raw] of Object.entries(data ?? {})) {
      try {
        root[queue] = JSON.parse(raw);
      } catch {
        // Skip malformed entries: a single bad queue must not break the build.
      }
    }
    return keepOnlyDefiniteSlots(
      root as Record<string, { days: { slots: { type: string }[] }[] }>,
    ) as SchedulesResponse;
  }
}
