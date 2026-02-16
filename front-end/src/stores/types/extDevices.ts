import { ObjectId } from "../../schemas";
import { BaseListState } from "./base";

export type ExtDeviceItem = {
    macAddress: string;
    fwVersion: string;
    fsVersion: string;
    uptime: number;
    updatedAt: string;
    userId: ObjectId | null;
    gridState: boolean | null;
};

export type ExtDevicesState = BaseListState<ExtDeviceItem>;
