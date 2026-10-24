import { describe, expect, it } from "vitest";
import { safeParse } from "valibot";
import { dashboardEditSchema, toDashboardEditConfig } from "./dashboardEdit";

describe("dashboardEditSchema", () => {
  it("accepts a nested outages schedule configuration", () => {
    const result = safeParse(dashboardEditSchema, {
      title: { en: "Dashboard", uk: "Панель" },
      outagesSchedule: {
        enable: true,
        region: "Kyiv",
        dso: "Yasno",
        queue: "1.1",
      },
    });

    expect(result.success).toBe(true);
  });

  it("rejects an enabled schedule with missing selections", () => {
    const result = safeParse(dashboardEditSchema, {
      title: { en: "Dashboard", uk: "Панель" },
      outagesSchedule: {
        enable: true,
        region: null,
        dso: null,
        queue: null,
      },
    });

    expect(result.success).toBe(false);
  });

  it("converts a legacy enabled configuration", () => {
    expect(toDashboardEditConfig({
      title: { en: "Dashboard", uk: "Панель" },
      enableOutagesSchedule: true,
      outagesScheduleQueue: "1.1",
    })).toEqual({
      title: { en: "Dashboard", uk: "Панель" },
      outagesSchedule: {
        enable: true,
        region: "Kyiv",
        dso: "Yasno",
        queue: "1.1",
      },
    });
  });

  it("normalizes a disabled configuration to empty nested values", () => {
    expect(toDashboardEditConfig({
      title: { en: "Dashboard", uk: "Панель" },
      outagesSchedule: null,
    }).outagesSchedule).toEqual({
      enable: false,
      region: null,
      dso: null,
      queue: null,
    });
  });
});
