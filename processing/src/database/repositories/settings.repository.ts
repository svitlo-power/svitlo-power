import { Injectable } from "@nestjs/common";
import { InjectModel } from "@nestjs/mongoose";
import { Model } from "mongoose";
import {
  SystemSettingDocument,
  SystemSettingSchemaClass,
} from "../../shared.js";

/**
 * Read-only access to `system_settings`.
 *
 * Mirrors `SettingsRepository.get_settings_by_keys` plus the typed getters from
 * `SettingsService`, including the fallback chain value → default_value →
 * caller default.
 */
@Injectable()
export class SettingsRepository {
  constructor(
    @InjectModel("SystemSetting")
    private readonly model: Model<SystemSettingDocument>,
  ) {}

  async getSettingsByKeys(
    keys: string[],
  ): Promise<Map<string, SystemSettingSchemaClass>> {
    if (keys.length === 0) return new Map();
    const documents = await this.model
      .find({ key: { $in: keys } })
      .lean<SystemSettingSchemaClass[]>()
      .exec();
    return new Map(documents.map((document) => [document.key, document]));
  }

  /** Current value of a setting, falling back to its default then `fallback`. */
  async getValue<T = unknown>(key: string, fallback: T): Promise<T> {
    const settings = await this.getSettingsByKeys([key]);
    const setting = settings.get(key);
    if (!setting) return fallback;
    if (setting.value !== null && setting.value !== undefined) {
      return setting.value as T;
    }
    if (setting.default_value !== null && setting.default_value !== undefined) {
      return setting.default_value as T;
    }
    return fallback;
  }

  async getNumber(key: string, fallback = 0): Promise<number> {
    const value = await this.getValue<unknown>(key, fallback);
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  async getInt(key: string, fallback = 0): Promise<number> {
    const value = await this.getValue<unknown>(key, fallback);
    const parsed = Number.parseInt(String(value), 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  async getText(key: string, fallback = ""): Promise<string> {
    const value = await this.getValue<unknown>(key, fallback);
    return value === null || value === undefined ? fallback : String(value);
  }

  async getBoolean(key: string, fallback = false): Promise<boolean> {
    const value = await this.getValue<unknown>(key, fallback);
    if (typeof value === "boolean") return value;
    if (typeof value === "string") {
      return ["true", "1", "yes", "on"].includes(value.toLowerCase());
    }
    return Boolean(value);
  }

  /**
   * Localized text setting. An empty map is treated as unset, matching
   * `SettingsService.get_localizable_text`.
   */
  async getLocalizableText(
    key: string,
    fallback: Record<string, string>,
  ): Promise<Record<string, string>> {
    const value = await this.getValue<unknown>(key, fallback);
    if (value === null || value === undefined) return fallback;
    if (typeof value === "object" && !Array.isArray(value)) {
      const record = value as Record<string, unknown>;
      const entries = Object.entries(record).filter(
        ([locale, text]) =>
          ["en", "uk"].includes(locale) && typeof text === "string",
      );
      if (entries.length === 0) return fallback;
      return Object.fromEntries(entries) as Record<string, string>;
    }
    throw new Error(`Setting '${key}' does not contain localized text`);
  }
}
