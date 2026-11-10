export type AppConfig = {
  disablePublicFrontend: boolean;
};

declare global {
  var __SVITLO_CONFIG__: Partial<AppConfig> | undefined;
}

export const isPublicFrontendDisabled = () =>
  globalThis.__SVITLO_CONFIG__?.disablePublicFrontend ?? false;
