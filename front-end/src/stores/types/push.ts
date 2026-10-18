import { LocalizableValue, ObjectId } from "../../schemas";
import { BaseListState } from "./base";

export type PushPlatform = "android" | "web";

export type PushDeviceItem = {
    id: ObjectId;
    platform: PushPlatform;
    language: string;
    enabled: boolean;
    disabledTopics: string[];
    buildings: ObjectId[];
    appVersion: string | null;
    createdAt: string;
    lastSeen: string;
};

export type PushTopicItem = {
    key: string;
    name: LocalizableValue;
    description: LocalizableValue;
    enabled: boolean;
    order: number;
    subscribers: number;
};

export type PushTestRequest = {
    title: string;
    body: string;
    route?: string;
    deviceId?: ObjectId;
    topic?: string;
};

export type PushSendResult = {
    successCount: number;
    failureCount: number;
    removedCount: number;
};

export type PushDevicesState = BaseListState<PushDeviceItem>;

export type PushTopicsState = BaseListState<PushTopicItem>;
