import { FC } from "react";
import { BuildingListItem, BuildingSummaryItem } from "../../../stores/types";
import { ActionIcon, Box, Group, Loader, SimpleGrid, Text } from "@mantine/core";
import { openBuildingEditDialog } from "./buildingEditDialog";
import { EditableBuildingCard } from "./editableBuildingCard";
import { BuildingCard } from "./buildingCard";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { BuildingEditType } from "../../../schemas";
import { TFunction } from "i18next";

type BuildingsViewProps = {
  t: TFunction;
  loading: boolean;
  loadingSummary: boolean;
  isAuthenticated: boolean;
  buildings: Array<BuildingListItem | BuildingEditType>;
  buildingsSummary: Array<BuildingSummaryItem>;
}

export const BuildingsView: FC<BuildingsViewProps> = ({
  t,
  loading,
  loadingSummary,
  isAuthenticated,
  buildings,
  buildingsSummary,
}) => {
  if (loading) {
    return (
      <Box w='100%' ta="center" py="xl">
        <Loader size="lg" />
        <Text mt="md" c="dimmed">
          {t('buildings.loading')}
        </Text>
      </Box>
    )
  }

  return <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="xl">
    {buildings.map((building, idx) => {
      const buildingSummary = buildingsSummary.find(f => f.id === building.id);
      return isAuthenticated
        ? <EditableBuildingCard
            t={t}
            key={`b_${idx}`}
            building={building as BuildingListItem}
            loadingSummary={loadingSummary}
            buildingSummary={buildingSummary}
            maxOrder={buildings.length}
          />
        : <BuildingCard
            t={t}
            key={`b_${idx}`}
            building={building as BuildingListItem}
            loadingSummary={loadingSummary}
            buildingSummary={buildingSummary}
          />
      })}

    {isAuthenticated && <Group justify="center" align="center">
      {t('buildings.add')}
      <ActionIcon
        radius="lg"
        size="lg"
        onClick={() =>
          openBuildingEditDialog({
            creating: true,
            title: t('buildings.add'),
          })
        }
      >
        <FontAwesomeIcon icon="plus" size="2x" />
      </ActionIcon>
    </Group>}
  </SimpleGrid>
;
}