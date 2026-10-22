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

export type PushTemplateParam = {
    key: string;
    value: number;
    default: number;
    min: number;
    max: number;
};

export type PushTemplateItem = {
    topic: string;
    enabled: boolean;
    title: Record<string, string>;
    body: Record<string, string>;
    route: string;
    shouldSend: string | null;
    macros: string | null;
    params: PushTemplateParam[];
    // Sample variables of the event; also used for editor autocompletion
    variables: Record<string, unknown>;
    updatedAt: string;
};

export type PushTemplateRequest = {
    enabled: boolean;
    title: Record<string, string>;
    body: Record<string, string>;
    route: string;
    shouldSend: string | null;
    macros: string | null;
    params: Record<string, number>;
};

export type PushTemplatePreviewItem = {
    language: string;
    title: string | null;
    body: string | null;
    route: string | null;
    error: string | null;
};

export type PushTemplatePreview = {
    shouldSend: boolean | null;
    shouldSendError: string | null;
    items: PushTemplatePreviewItem[];
};

export type PushDeliveryStatus =
    | "pending"
    | "sent"
    | "failed"
    | "skipped_topic_disabled"
    | "skipped_template_disabled"
    | "skipped_condition"
    | "no_recipients";

export type PushDeliveryItem = {
    id: ObjectId;
    dedupKey: string;
    topic: string;
    summary: Record<string, string>;
    buildingId: ObjectId | null;
    status: PushDeliveryStatus;
    recipients: number;
    recipientsByLanguage: Record<string, number>;
    successCount: number;
    failureCount: number;
    invalidRemoved: number;
    createdAt: string;
    error: string | null;
};

export type AnnouncementItem = {
    id: ObjectId;
    title: Record<string, string>;
    body: Record<string, string>;
    createdAt: string;
    delivery: PushDeliveryItem | null;
};

export type AnnouncementRequest = {
    title: Record<string, string>;
    body: Record<string, string>;
};

export type PushTemplatesState = BaseListState<PushTemplateItem>;

export type PushDeliveriesState = BaseListState<PushDeliveryItem>;

export type AnnouncementsState = BaseListState<AnnouncementItem>;
