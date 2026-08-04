import { ObjectId } from "../../schemas";
import { BaseState } from "./base";

export type ServerStationConnectionItem = {
  id: ObjectId;
  name: string;
  baseUrl: string;
  appId: string;
  email: string;
  syncStationsOnPoll: boolean;
};

export type StationConnectionEditItem = {
  name: string;
  baseUrl: string;
  appId: string;
  appSecret: string;
  email: string;
  password: string;
  syncStationsOnPoll: boolean;
};

export type StationConnectionsState = BaseState & {
  connections: Array<ServerStationConnectionItem>;
};
