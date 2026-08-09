import { MessageEdit, ObjectId } from "../../schemas";
import { BaseEditableState, BaseResponse } from "./base";

export type BaseServerMessageListItem = {
  id?: ObjectId;
  name: string;
  stations: ObjectId[];
  lastSentTime: Date;
  enabled: boolean;
};

export type BaseServerMessageItem = BaseServerMessageListItem & {
  channelId: string;
  messageTemplate: string;
  shouldSendTemplate: string;
  timeoutTemplate: string;
  botId: ObjectId;
};

type MessageDetailsItem = {
  channelName: string;
  botName: string;
};

export type ServerMessageListItem = BaseServerMessageListItem & MessageDetailsItem & {
  changed: boolean;
};

export type ServerMessageItem = BaseServerMessageItem & MessageDetailsItem;

export type TemplatePreview = {
  shouldSend: boolean;
  timeout: number;
  message: string;
  nextSendTime: Date;
  data?: Record<string, unknown>;
};

export type TemplatePreviewResponse = BaseResponse & TemplatePreview;

export type TemplatePreviewRequest = Omit<BaseServerMessageItem, 'id'|'name'|'lastSentTime'|'enabled'>;

export type MessagesState = BaseEditableState & {
  messages: Array<ServerMessageListItem>;
  editingMessage?: MessageEdit;
  templatePreview?: TemplatePreview;
  loadingPreview: boolean;
  previewError?: string;
  changed: boolean;
};

export type SaveMessageResponse = {
  success: boolean;
  id: number;
};

