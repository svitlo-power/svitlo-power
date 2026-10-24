import * as v from 'valibot';
import { localizableValueSchema, LocalizableValue } from './base';

export const outagesScheduleSchema = v.object({
  enable: v.boolean(),
  region: v.nullable(v.string()),
  dso: v.nullable(v.string()),
  queue: v.nullable(v.string()),
});

export const dashboardEditSchema = v.pipe(
  v.object({
    title: localizableValueSchema,
    outagesSchedule: outagesScheduleSchema,
  }),
  v.check(
    ({ outagesSchedule }) => !outagesSchedule.enable || Boolean(
      outagesSchedule.region?.trim()
      && outagesSchedule.dso?.trim()
      && outagesSchedule.queue?.trim(),
    ),
    'validation.outagesScheduleSelectionRequired',
  ),
);

export type OutagesScheduleConfig = v.InferInput<typeof outagesScheduleSchema>;
export type DashboardEditType = v.InferInput<typeof dashboardEditSchema>;

export type DashboardConfigInput = {
  title: LocalizableValue;
  outagesSchedule?: OutagesScheduleConfig | null;
  enableOutagesSchedule?: boolean;
  outagesScheduleQueue?: string | null;
};

export const toDashboardEditConfig = (config: DashboardConfigInput): DashboardEditType => ({
  title: config.title,
  outagesSchedule: config.outagesSchedule ?? {
    enable: config.enableOutagesSchedule ?? false,
    region: config.enableOutagesSchedule ? 'Kyiv' : null,
    dso: config.enableOutagesSchedule ? 'Yasno' : null,
    queue: config.enableOutagesSchedule ? config.outagesScheduleQueue ?? null : null,
  },
});
