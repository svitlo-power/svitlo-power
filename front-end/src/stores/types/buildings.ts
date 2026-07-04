import { MantineColor } from "@mantine/core";
import { BaseState } from "./base";
import { BuildingEditType, LocalizableValue, ObjectId } from "../../schemas";


export type BuildingListItem = {
  id?: ObjectId;
  name: LocalizableValue;
  color: MantineColor;
  hasBoundStation: boolean;
  order: number;
};

export type BuildingsState = BaseState & {
  items: Array<BuildingListItem>;
  edittedItems: Array<BuildingEditType & { isNew?: boolean }>;
  editingItem?: BuildingEditType;
  changed: boolean;
  globalId: number;
};
