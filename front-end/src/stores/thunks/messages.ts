import { createAsyncThunk } from "@reduxjs/toolkit";
import { BaseSaveDataResponse, ServerMessageListItem, 
  TemplatePreviewRequest, TemplatePreviewResponse } from "../types";
import { RootState } from "../store";
import apiClient from "../../utils/apiClient";
import { MessageEdit, ObjectId } from "../../schemas";
import { getErrorMessage } from "../../utils";
import { messageStateSaved } from "../slices";

export const fetchMessages = createAsyncThunk('messages/fetchMessages', async (_, thunkAPI) => {
  try {
    const response = await apiClient.get<Array<ServerMessageListItem>>('/messages/messages');
    return response.data;
  } catch (error: unknown) {
    return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to fetch messages');
  }
});

export type ChannelRequest = {
  channelId: ObjectId,
  botId: ObjectId,
};

export const getChannel = createAsyncThunk<string, ChannelRequest>(
  'messages/getChannel',
  async (request) => {
    try {
      const response = await apiClient.post('/messages/getChannel', request);
      return response.data['channelName'];
    } catch (error: unknown) {
      return Promise.reject(getErrorMessage(error) || 'Failed to fetch messages');
    }
  });

export const editMessage = createAsyncThunk<MessageEdit, ObjectId>('messages/editMessage',
    async (message_id: ObjectId): Promise<MessageEdit> => {
  try {
    const response = await apiClient.get<MessageEdit>(`/messages/message/${message_id}`);
    return response.data;
  } catch (error: unknown) {
    return Promise.reject(getErrorMessage(error) || 'Failed to fetch messages');
  }
});

type TemplatePreviewArgs = {
  id?: ObjectId;
  name: string;
  stations: ObjectId[];
  templateMacros: string;
  shouldSendTemplate: string;
  timeoutTemplate: string;
  messageTemplate: string;
  language: string;
};

export const getTemplatePreview = createAsyncThunk<TemplatePreviewResponse, TemplatePreviewArgs>(
    'messages/templatePreview', async (args, { getState, rejectWithValue, fulfillWithValue }) => {
  try {
    const state = getState() as RootState;
    const message = state.messages.editingMessage;
    if (!message) {
      return rejectWithValue('No message is currently editing');
    }
    const request = {
      id: args.id,
      name: args.name,
      botId: message.botId,
      channelId: message.channelId,
      templateMacros: args.templateMacros,
      messageTemplate: args.messageTemplate,
      shouldSendTemplate: args.shouldSendTemplate,
      timeoutTemplate: args.timeoutTemplate,
      stations: args.stations,
      language: args.language,
    } as TemplatePreviewRequest;
    const response = await apiClient.post<TemplatePreviewResponse>('/messages/getPreview', request);
    if (response.data.success) {
      return fulfillWithValue(response.data);
    } else {
      return rejectWithValue(response.data);
    }
  } catch (error: unknown) {
    return rejectWithValue(getErrorMessage(error) || 'Failed to generate template preview');
  }
});

export const createMessage = createAsyncThunk('messages/createMessage', async (_,
    { getState, fulfillWithValue, dispatch, rejectWithValue }) => {
  try {
    const state = getState() as RootState;
    const data = {
      ...state.messages.editingMessage
    };
    const response = await apiClient.post<BaseSaveDataResponse>('/messages', data);
    dispatch(fetchMessages());
    return fulfillWithValue(response.data.id);
  } catch (error: unknown) {
    return rejectWithValue(getErrorMessage(error) || 'Failed to save message');
  }
});

export const updateMessage = createAsyncThunk('messages/updateMessage', async (messageId: ObjectId,
    { getState, fulfillWithValue, dispatch, rejectWithValue }) => {
  try {
    const state = getState() as RootState;
    const data = {
      ...state.messages.editingMessage
    };
    const response = await apiClient.put<BaseSaveDataResponse>(`/messages/${messageId}`, data);
    dispatch(fetchMessages());
    return fulfillWithValue(response.data.id);
  } catch (error: unknown) {
    return rejectWithValue(getErrorMessage(error) || 'Failed to save message');
  }
});

export const saveMessageStates = createAsyncThunk('messages/saveMessageStates', async (_, { getState, dispatch }) => {
  try {
    const state = getState() as RootState;
    const messagesState = state.messages;
    const promises = messagesState.messages.filter(s => s.changed).map(async message => {
      const serverDto = {
        enabled: message.enabled,
      } as ServerMessageListItem;
      const response = await apiClient.patch<BaseSaveDataResponse>(`/messages/${message.id}/state`, serverDto);
      dispatch(messageStateSaved(response.data.id));
    });
    await Promise.all(promises);
    dispatch(fetchMessages());
  } catch (error: unknown) {
    console.error(error);
  }
});