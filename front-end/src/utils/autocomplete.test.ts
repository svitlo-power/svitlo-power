import { describe, expect, it } from "vitest";
import { templateVariablesFromSample } from "./autocomplete";

describe("templateVariablesFromSample", () => {
  it("collects object members, list item members and plain values", () => {
    const variables = templateVariablesFromSample({
      building: { id: "1", name: { uk: "Будинок", en: "Building" } },
      slots: [{ start: "08:00", end: "12:00" }],
      soc: 18,
    }, ["lang", "now"]);

    expect(variables.building).toEqual(["id", "name"]);
    expect(variables.name).toEqual(["uk", "en"]);
    expect(variables.slots).toEqual(["start", "end"]);
    expect(variables.soc).toEqual([]);
    expect(variables.lang).toEqual([]);
    expect(variables.now).toEqual([]);
  });

  it("keeps an empty list as a plain variable", () => {
    expect(templateVariablesFromSample({ previous_slots: [] })).toEqual({ previous_slots: [] });
  });
});
