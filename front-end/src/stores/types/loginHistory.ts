import { ObjectId } from "../../schemas";
import { BaseListState } from "./base";

export type LoginHistoryItem = {
  id?: ObjectId;
  loginTime: string;
  ipAddress?: string | null;
};

export type LoginHistoryState = BaseListState<LoginHistoryItem>;
