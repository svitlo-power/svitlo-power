export interface LocalizableValue {
  [language: string]: string;
}

export interface Building {
  id: string | null;
  name: LocalizableValue;
  color: string;
  hasBoundStation: boolean;
  order: number;
}

export interface BuildingSummary {
  id: string;
  isGridAvailable: boolean | null;
  gridAvailabilityPct?: number | null;
  hasMixedReporterStates?: boolean | null;
  batteryPercent: number | null;
  isCharging: boolean | null;
  isDischarging: boolean | null;
  isOffline: boolean | null;
  batteryDischargeTime: string | null;
  batteryChargeTime: string | null;
  consumptionPower: string | null;
  chargeSource: string | null;
  chargePower: number | null;
}

export interface DashboardConfig {
  title: LocalizableValue;
  outagesSchedule: {
    enable: boolean;
    regionId: number;
    dsoId: number;
    queue: string;
  } | null;
}

export interface PowerLogPeriod {
  startTime: string;
  endTime: string;
  isAvailable: boolean;
  durationSeconds: number;
}

export interface PowerLogs {
  periods: PowerLogPeriod[];
  totalAvailableSeconds: number;
  totalUnavailableSeconds: number;
  totalGeneratorSeconds: number | null;
  totalSeconds: number;
}

export interface OutageSchedule {
  days: Array<Record<string, unknown>>;
  updatedOn: string;
}

export interface PushDevice {
  id: string;
  platform: string;
  language: string;
  enabled: boolean;
  disabledTopics: string[];
  buildings: string[];
  appVersion: string | null;
  createdAt: string;
  lastSeen: string;
}

export interface PushTopic {
  key: string;
  name: LocalizableValue;
  description: LocalizableValue;
}

export interface DeviceRegistration {
  token: string;
  platform: "android" | "ios";
  language?: string;
  appVersion?: string;
}

export interface DeviceSubscriptions {
  token: string;
  enabled?: boolean;
  disabledTopics?: string[];
  buildings?: string[];
}

export class InternalApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail: unknown,
  ) {
    super(message);
    this.name = "InternalApiError";
  }
}

export class InternalApiClient {
  private readonly baseUrl: string;

  constructor(
    baseUrl: string,
    private readonly serviceToken: string,
    private readonly timeoutMs = 12_000,
    private readonly fetcher: typeof fetch = fetch,
  ) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  getBuildings(): Promise<Building[]> {
    return this.request("/dashboard/buildings");
  }

  getBuildingSummaries(buildingIds: string[]): Promise<BuildingSummary[]> {
    return this.request("/dashboard/buildings/summary", {
      method: "POST",
      body: JSON.stringify({ buildingIds }),
    });
  }

  getDashboardConfig(): Promise<DashboardConfig> {
    return this.request("/dashboard/config");
  }

  getPowerLogs(
    buildingId: string,
    startDate: string,
    endDate: string,
  ): Promise<PowerLogs> {
    return this.request(
      `/dashboard/buildings/${encodeURIComponent(buildingId)}/power-logs`,
      {
        method: "POST",
        body: JSON.stringify({ startDate, endDate }),
      },
    );
  }

  getOutageSchedule(queue: string): Promise<OutageSchedule> {
    return this.request(`/outages-schedule/${encodeURIComponent(queue)}`);
  }

  registerDevice(device: DeviceRegistration): Promise<PushDevice> {
    return this.request("/push/devices", {
      method: "POST",
      body: JSON.stringify(device),
    });
  }

  getDevice(token: string): Promise<PushDevice> {
    return this.request("/push/devices/current", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  }

  updateSubscriptions(subscriptions: DeviceSubscriptions): Promise<PushDevice> {
    return this.request("/push/devices/subscriptions", {
      method: "POST",
      body: JSON.stringify(subscriptions),
    });
  }

  unregisterDevice(token: string): Promise<{ success: true }> {
    return this.request("/push/devices/unregister", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  }

  getPushTopics(): Promise<PushTopic[]> {
    return this.request("/push/topics");
  }

  getHealth(): Promise<{ status: "ok" }> {
    return this.request("/health");
  }

  getReadiness(): Promise<{
    status: "ready" | "not_ready";
    checks: Record<string, string>;
  }> {
    return this.request("/ready");
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    if (!this.serviceToken) {
      throw new InternalApiError(
        "Internal API is not configured",
        503,
        "Dependency unavailable",
      );
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetcher(`${this.baseUrl}${path}`, {
        ...init,
        signal: controller.signal,
        headers: {
          Authorization: `Bearer ${this.serviceToken}`,
          ...(init.body ? { "Content-Type": "application/json" } : {}),
          ...init.headers,
        },
      });
      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        if (response.ok) {
          throw new InternalApiError(
            "Internal API returned an invalid response",
            502,
            "Dependency unavailable",
          );
        }
      }
      if (!response.ok) {
        const detail =
          payload && typeof payload === "object" && "detail" in payload
            ? (payload as { detail: unknown }).detail
            : undefined;
        throw new InternalApiError(
          `Internal API request failed with status ${response.status}`,
          response.status,
          detail,
        );
      }
      return payload as T;
    } catch (error) {
      if (error instanceof InternalApiError) throw error;
      if (controller.signal.aborted) {
        throw new InternalApiError(
          "Internal API request timed out",
          504,
          undefined,
        );
      }
      throw new InternalApiError("Internal API is unavailable", 503, undefined);
    } finally {
      clearTimeout(timeout);
    }
  }
}
