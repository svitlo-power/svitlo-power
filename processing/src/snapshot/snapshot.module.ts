import { Module } from "@nestjs/common";
import { DatabaseModule } from "../database/database.module.js";
import { RepositoriesModule } from "../database/repositories/repositories.module.js";
import { SnapshotBuilder } from "./snapshot.builder.js";
import { SnapshotValidator } from "./snapshot.validator.js";

@Module({
  imports: [DatabaseModule, RepositoriesModule],
  providers: [SnapshotBuilder, SnapshotValidator],
  exports: [SnapshotBuilder, SnapshotValidator],
})
export class SnapshotModule {}
