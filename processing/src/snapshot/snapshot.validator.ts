import { Inject, Injectable } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import {
  isObjectId,
  isStrictIsoDateTime,
} from "@svitlo-power/shared-typescript";
import { DashboardSnapshot } from "../shared.js";
import { processingConfig } from "../config/processing.config.js";

export interface SnapshotValidatorResult {
  valid: boolean;
  errors: string[];
}

/**
 * Validates a built snapshot against the `DashboardSnapshot v1` contract before
 * it is allowed anywhere near Redis.
 *
 * The checks mirror `docs/architecture/snapshot-schema.json`; they are hand
 * written so the service does not need a JSON-Schema dependency.
 */
@Injectable()
export class SnapshotValidator {
  constructor(
    @Inject(processingConfig.KEY)
    private readonly config: ConfigType<typeof processingConfig>,
  ) {}

  validate(snapshot: DashboardSnapshot): SnapshotValidatorResult {
    const errors: string[] = [];

    if (!Number.isInteger(snapshot.epoch) || snapshot.epoch < 1) {
      errors.push("epoch must be a positive integer");
    }
    if (!Number.isInteger(snapshot.version) || snapshot.version < 1) {
      errors.push("version must be a positive integer");
    }
    if (
      typeof snapshot.generatedAt !== "string" ||
      !isStrictIsoDateTime(snapshot.generatedAt)
    ) {
      errors.push("generatedAt must be an ISO 8601 timestamp");
    }
    if (!Array.isArray(snapshot.buildings)) {
      errors.push("buildings must be an array");
    } else {
      snapshot.buildings.forEach((building, index) => {
        errors.push(...this.validateBuilding(building, index));
      });
    }

    const title = snapshot.config?.title;
    if (!title || typeof title !== "object" || Array.isArray(title)) {
      errors.push("config.title must be an object");
    } else {
      for (const locale of Object.keys(title)) {
        if (!["en", "uk"].includes(locale)) {
          errors.push(`config.title has unsupported locale '${locale}'`);
        }
      }
    }

    if (snapshot.config?.outagesSchedule) {
      const schedule = snapshot.config.outagesSchedule;
      if (typeof schedule.enable !== "boolean") {
        errors.push("config.outagesSchedule.enable must be a boolean");
      }
      if (schedule.enable && !schedule.queue) {
        errors.push("config.outagesSchedule.queue is required when enabled");
      }
    }

    if (
      !snapshot.outagesSchedules ||
      typeof snapshot.outagesSchedules !== "object" ||
      Array.isArray(snapshot.outagesSchedules)
    ) {
      errors.push("outagesSchedules must be an object");
    }

    return { valid: errors.length === 0, errors };
  }

  private validateBuilding(building: unknown, index: number): string[] {
    const prefix = `buildings[${index}]`;
    if (typeof building !== "object" || building === null) {
      return [`${prefix} must be an object`];
    }
    const record = building as Record<string, unknown>;
    const errors: string[] = [];
    if (typeof record.id !== "string" || !isObjectId(record.id)) {
      errors.push(`${prefix}.id must be a 24-char hex ObjectId`);
    }
    if (
      typeof record.name !== "object" ||
      record.name === null ||
      Array.isArray(record.name)
    ) {
      errors.push(`${prefix}.name must be an object`);
    }
    if (typeof record.color !== "string") {
      errors.push(`${prefix}.color must be a string`);
    }
    if (!Number.isInteger(record.order)) {
      errors.push(`${prefix}.order must be an integer`);
    }
    if (typeof record.hasBoundStation !== "boolean") {
      errors.push(`${prefix}.hasBoundStation must be a boolean`);
    }
    if (typeof record.chargeSource !== "string") {
      errors.push(`${prefix}.chargeSource must be a string`);
    }
    return errors;
  }
}
