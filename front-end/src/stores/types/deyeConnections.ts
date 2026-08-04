import { ObjectId } from "../../schemas";
import { BaseState } from "./base";

export type ServerDeyeConnectionItem = {
  id: ObjectId;
  name: string;
  baseUrl: string;
  appId: string;
  email: string;
  syncStationsOnPoll: boolean;
};

export type DeyeConnectionEditItem = {
  name: string;
  baseUrl: string;
  appId: string;
  appSecret: string;
  email: string;
  password: string;
  syncStationsOnPoll: boolean;
};

export type DeyeConnectionsState = BaseState & {
  connections: Array<ServerDeyeConnectionItem>;
};
