import { Action, combineReducers } from "redux";
import {
  authReducer,
  botsReducer,
  chatsReducer,
  messagesReducer,
  stationsReducer,
  stationsDataReducer,
  buildingsReducer,
  stationConnectionsReducer,
  usersReducer,
  extDataReducer,
  dashboardConfigReducer,
  visitCounterReducer,
  outagesScheduleReducer,
  powerLogsReducer,
  buildingsSummaryReducer,
  extDevicesReducer,
  loginHistoryReducer,
  appReducer,
} from "./slices";
import { logout } from "./slices";
import { lookupValuesReducer } from "./slices/lookupValues";

const combinedReducers = combineReducers({
  ["auth"]: authReducer,
  ["bots"]: botsReducer,
  ["buildings"]: buildingsReducer,
  ["buildingsSummary"]: buildingsSummaryReducer,
  ["extData"]: extDataReducer,
  ["chats"]: chatsReducer,
  ["dashboardConfig"]: dashboardConfigReducer,
  ["stationConnections"]: stationConnectionsReducer,
  ["lookupValues"]: lookupValuesReducer,
  ["stations"]: stationsReducer,
  ["stationsData"]: stationsDataReducer,
  ["messages"]: messagesReducer,
  ["outagesSchedule"]: outagesScheduleReducer,
  ["powerLogs"]: powerLogsReducer,
  ["users"]: usersReducer,
  ["visitCounter"]: visitCounterReducer,
  ["extDevices"]: extDevicesReducer,
  ["loginHistory"]: loginHistoryReducer,
  ["app"]: appReducer,
});

type RootState = ReturnType<typeof combinedReducers>;

export const rootReducer = (state: RootState | undefined, action: Action) => {
  if (action.type === logout.type) {
    state = undefined;
  }
  return combinedReducers(state, action);
};