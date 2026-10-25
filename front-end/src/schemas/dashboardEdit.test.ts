import { describe, expect, it } from "vitest";
import { safeParse } from "valibot";
import { dashboardEditSchema, toDashboardEditConfig } from "./dashboardEdit";

describe("dashboardEditSchema", () => {
  it("accepts a nested outages schedule configuration", () => {
    const result = safeParse(dashboardEditSchema, {
      title: { en: "Dashboard", uk: "Панель" },
      outagesSchedule: {
        enable: true,
        regionId: 25,
        dsoId: 902,
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
        regionId: null,
        dsoId: null,
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
        regionId: "Kyiv",
        dsoId: "Yasno",
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
      regionId: null,
      dsoId: null,
      queue: null,
    });
  });
});
