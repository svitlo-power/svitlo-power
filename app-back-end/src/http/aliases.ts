import { Expose, Transform } from "class-transformer";

/**
 * Pydantic models used `populate_by_name=True`, so clients could send either
 * the camelCase alias or the snake_case field name. Accept both; the camelCase
 * alias wins when both are present, and `fallback` applies when neither is.
 */
export function AcceptsAlias(
  camelCase: string,
  snakeCase: string,
  fallback?: () => unknown,
): PropertyDecorator {
  return (target, property) => {
    Expose()(target, property);
    Transform(({ obj }: { obj: Record<string, unknown> }) => {
      const value = obj[camelCase] ?? obj[snakeCase];
      return value === undefined && fallback ? fallback() : value;
    })(target, property);
  };
}
