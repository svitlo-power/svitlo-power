import { Completion, CompletionContext, CompletionResult, CompletionSource } from "@codemirror/autocomplete";

export type TemplateVariables = Record<string, Array<string>>;

const messageVariables: TemplateVariables = {
  "station": ["current", "previous", "name", "battery_capacity",
    "grid_interconnection_type", "connection_status"],
  "stations": ["current", "previous", "name", "battery_capacity",
    "grid_interconnection_type", "connection_status"],
  "current": ["station_id", "battery_power", "battery_soc", "charge_power", 
    "code", "consumption_power", "discharge_power", "generation_power", 
    "grid_power", "irradiate_intensity", "last_update_time", "msg", 
    "purchase_power", "request_id", "wire_power", "name", 
    "grid_interconnection_type", "connection_status"],
  "previous": ["station_id", "battery_power", "battery_soc", "charge_power",
    "code", "consumption_power", "discharge_power", "generation_power",
    "grid_power", "irradiate_intensity", "last_update_time", "msg",
    "purchase_power", "request_id", "wire_power"],
};

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

/**
 * Builds the autocompletion map from sample template data: every object or list of objects
 * becomes a variable with its keys as members, so `building.` and `{% for s in slots %}` complete.
 */
export function templateVariablesFromSample(sample: Record<string, unknown>, extra: string[] = []): TemplateVariables {
  const result: TemplateVariables = {};
  const visit = (name: string, value: unknown) => {
    const item = Array.isArray(value) ? value.find(isObject) : value;
    if (!isObject(item)) {
      result[name] ??= [];
      return;
    }
    result[name] = Object.keys(item);
    Object.entries(item).forEach(([key, child]) => {
      if (isObject(child) || Array.isArray(child)) {
        visit(key, child);
      }
    });
  };
  Object.entries(sample).forEach(([name, value]) => visit(name, value));
  extra.forEach((name) => { result[name] ??= []; });
  return result;
}

export function createJinja2Autocomplete(variables: TemplateVariables): CompletionSource {
  return (context: CompletionContext): CompletionResult | null => completeJinja2(variables, context);
}

export function jinja2Autocomplete(context: CompletionContext): CompletionResult | null {
  return completeJinja2(messageVariables, context);
}

function completeJinja2(variables: TemplateVariables, context: CompletionContext): CompletionResult | null {
  const word = context.matchBefore(/\w*/);
  if (!word || (word.from === word.to && !context.explicit)) {
    return null;
  }

  const suggestions: Completion[] = [];

  Object.keys(variables).forEach((variable) => {
    suggestions.push({
      label: variable,
      type: "variable",
    });
  });

  const line = context.state.doc.lineAt(context.pos).text;

  const matchArray = line.match(/(\w+)\.(\w*)$/);
  if (matchArray) {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [_, variable, partialMember] = matchArray;
    if (variables[variable]) {
      variables[variable].forEach((member) => {
        if (member.startsWith(partialMember)) {
          suggestions.push({
            label: `${member}`,
            type: "property",
          });
        }
      });
    }
  }

  const matchLoop = line.match(/for\s+(\w+)\s+in\s+(\w+)/);
  if (matchLoop) {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [_, loopVar, arrayVar] = matchLoop;
    if (variables[arrayVar]) {
      variables[arrayVar].forEach((member) => {
        suggestions.push({
          label: `${loopVar}.${member}`,
          type: "property",
        });
      });
    }
  }

  return {
    from: word.from,
    options: suggestions,
  };
}
