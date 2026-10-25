import * as v from 'valibot';
import { localizableValueSchema, LocalizableValue } from './base';
import {
  LEGACY_YASNO_PROVIDER_NAME,
  LEGACY_YASNO_REGION_NAME,
} from '../constants/outagesSchedule';

export const outagesScheduleSchema = v.object({
  enable: v.boolean(),
  regionId: v.nullable(v.union([v.number(), v.string()])),
  dsoId: v.nullable(v.union([v.number(), v.string()])),
  queue: v.nullable(v.string()),
});

export const dashboardEditSchema = v.pipe(
  v.object({
    title: localizableValueSchema,
    outagesSchedule: outagesScheduleSchema,
  }),
  v.check(
    ({ outagesSchedule }) => !outagesSchedule.enable || Boolean(
      outagesSchedule.regionId !== null
      && outagesSchedule.dsoId !== null
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
    regionId: config.enableOutagesSchedule ? LEGACY_YASNO_REGION_NAME : null,
    dsoId: config.enableOutagesSchedule ? LEGACY_YASNO_PROVIDER_NAME : null,
    queue: config.enableOutagesSchedule ? config.outagesScheduleQueue ?? null : null,
  },
});
