import { ObjectId } from "../../schemas";
import { BaseState } from "./base";

export type BaseServerStationItem = {
  id: ObjectId;
  enabled: boolean;
  order: number;
  batteryCapacity: number;
};

export type ServerStationItem = BaseServerStationItem & {
  stationName: string;
  connectionStatus: string;
  gridInterconnectionType: string;
  lastUpdateTime: Date;
  connectionName: string | null;
};

export type StationItem = ServerStationItem & {
  changed: boolean;
}

export type StationsState = BaseState & {
  stations: Array<StationItem>;
}