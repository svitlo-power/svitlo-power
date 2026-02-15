export enum EventType {
  VisitsUpdated = "visits_updated",
  DashboardConfigUpdated = "dashboard_config_updated",
  StationDataUpdated = "station_data_updated",
  BuildingsUpdated = "buildings_updated",
  ExtDataUpdated = "ext_data_updated",
  ExtDeviceUpdated = "ext_device_updated",
  OutagesUpdated = "outages_updated",
  MessagesUpdated = "messages_updated",
  ChatsUpdated = "chats_updated",
  Ping = "ping",
  Shutdown = "shutdown",
};

export type EventItem = {
  type: EventType;
  data: Record<string, string>;
  private: boolean;
  user?: string;
};
