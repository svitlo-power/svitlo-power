import { Logger, Module } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { createClient, RedisClientType } from "redis";
import { appConfig } from "../../config/app.config.js";
import { REDIS_READER, REDIS_SUBSCRIBER } from "../../tokens.js";
import { RedisConnections } from "./redis-connections.service.js";

function createRedisClient(url: string, clientName: string): RedisClientType {
  const client = createClient({ url });
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
      inject: [appConfig.KEY],
      useFactory: async (config: ConfigType<typeof appConfig>) => {
        const client = createRedisClient(config.redisUrl, "reader");
        await client.connect();
        return client;
      },
    },
    {
      provide: REDIS_SUBSCRIBER,
      inject: [appConfig.KEY],
      useFactory: async (config: ConfigType<typeof appConfig>) => {
        const client = createRedisClient(config.redisUrl, "subscriber");
        await client.connect();
        return client;
      },
    },
    RedisConnections,
  ],
  exports: [REDIS_READER, REDIS_SUBSCRIBER, RedisConnections],
})
export class RedisModule {}
