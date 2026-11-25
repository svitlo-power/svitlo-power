import { Logger, Module } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { createClient, RedisClientType } from "redis";
import { processingConfig } from "../../config/processing.config.js";
import { REDIS_READER, REDIS_SUBSCRIBER, REDIS_WRITER } from "../../tokens.js";
import { RedisConnections } from "./redis-connections.service.js";

function createRedisClient(url: string, clientName: string): RedisClientType {
  // Fail fast while disconnected instead of queueing commands: the shadow
  // publisher must never silently buffer writes intended for Redis.
  const client = createClient({ url, disableOfflineQueue: true });
  const logger = new Logger("Redis");
  client.on("error", (error) =>
    logger.error(`Redis ${clientName} connection error: ${error.name}`),
  );
  return client as RedisClientType;
}

@Module({
  providers: [
    {
      provide: REDIS_READER,
      inject: [processingConfig.KEY],
      useFactory: async (config: ConfigType<typeof processingConfig>) => {
        const client = createRedisClient(config.redisUrl, "reader");
        await client.connect();
        return client;
      },
    },
    {
      provide: REDIS_WRITER,
      inject: [processingConfig.KEY],
      useFactory: async (config: ConfigType<typeof processingConfig>) => {
        const client = createRedisClient(config.redisUrl, "writer");
        await client.connect();
        return client;
      },
    },
    {
      // A subscriber-mode client cannot run ordinary commands, so it needs its
      // own connection. It is created lazily by the module that uses it so a
      // deployment that never subscribes does not open a third socket.
      provide: REDIS_SUBSCRIBER,
      inject: [processingConfig.KEY],
      useFactory: async (config: ConfigType<typeof processingConfig>) => {
        const client = createRedisClient(config.redisUrl, "subscriber");
        await client.connect();
        return client;
      },
    },
    RedisConnections,
  ],
  exports: [REDIS_READER, REDIS_WRITER, REDIS_SUBSCRIBER, RedisConnections],
})
export class RedisModule {}
