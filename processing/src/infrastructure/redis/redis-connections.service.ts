import { Inject, Injectable, OnModuleDestroy } from "@nestjs/common";
import { RedisClientType } from "redis";
import { REDIS_READER, REDIS_WRITER } from "../../tokens.js";

@Injectable()
export class RedisConnections implements OnModuleDestroy {
  constructor(
    @Inject(REDIS_READER) readonly reader: RedisClientType,
    @Inject(REDIS_WRITER) readonly writer: RedisClientType,
  ) {}

  async onModuleDestroy(): Promise<void> {
    await Promise.all([
      this.reader.quit().catch(() => undefined),
      this.writer.quit().catch(() => undefined),
    ]);
  }

  async ping(): Promise<boolean> {
    try {
      await this.reader.ping();
      return true;
    } catch {
      return false;
    }
  }
}
