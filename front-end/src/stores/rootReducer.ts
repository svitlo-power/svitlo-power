import { Action, combineReducers } from "redux";
import {
  authReducer,
  botsReducer,
  chatsReducer,
  messagesReducer,
  stationsReducer,
  stationsDataReducer,
  buildingsReducer,
  usersReducer,
  extDataReducer,
  dashboardConfigReducer,
  visitCounterReducer,
  outagesScheduleReducer,
  powerLogsReducer,
  buildingsSummaryReducer,
  extDevicesReducer,
} from "./slices";
import { logout } from "./slices";
import { lookupValuesReducer } from "./slices/lookupValues";

const appReducer = combineReducers({
  ['auth']: authReducer,
  ['bots']: botsReducer,
  ['buildings']: buildingsReducer,
  ['buildingsSummary']: buildingsSummaryReducer,
  ['extData']: extDataReducer,
  ['chats']: chatsReducer,
  ['dashboardConfig']: dashboardConfigReducer,
  ['lookupValues']: lookupValuesReducer,
  ['stations']: stationsReducer,
  ['stationsData']: stationsDataReducer,
  ['messages']: messagesReducer,
  ['outagesSchedule']: outagesScheduleReducer,
  ['powerLogs']: powerLogsReducer,
  ['users']: usersReducer,
  ['visitCounter']: visitCounterReducer,
  ['extDevices']: extDevicesReducer,
});

type RootState = ReturnType<typeof appReducer>;

export const rootReducer = (state: RootState | undefined, action: Action) => {
  if (action.type === logout.type) {
    state = undefined;
  }
  return appReducer(state, action);
};
