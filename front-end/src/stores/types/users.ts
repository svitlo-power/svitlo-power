import { ObjectId } from "../../schemas";
import { BaseEditableState } from "./base";

export enum UserReportMode {
  PING = 'ping',
  EVENT = 'event',
}

export type BaseServerUserItem = {
  id?: ObjectId;
  name: string;
  password?: string;
  isActive: boolean;
  isReporter: boolean;
  apiKey?: string | null;
  reportMode?: UserReportMode;
};

export type ServerUserItem = BaseServerUserItem & {
  id: ObjectId;
};

export type UserItem = ServerUserItem & {
  changed: boolean;
};

export type UsersState = BaseEditableState & {
  users: Array<UserItem>;
};

export type GenerateTokenResponse = {
  success: boolean;
  token?: string;
  error?: string;
};

