import { FC, ReactNode, useCallback, useMemo } from "react"
import { BuildingListItem, BuildingSummaryItem, ChargeSource } from "../../../stores/types";
import { StatsCard } from "../../../components";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconName } from "@fortawesome/free-solid-svg-icons";
import { openPowerLogsDialog } from "../../../dialogs";
import { ProgressProps, useMantineTheme } from "@mantine/core";
import { isChristmasSeason } from "../../../utils";
import i18n from "../../../i18n";
import { TFunction } from "i18next";

export type BuildingCardProps = {
  t: TFunction;
  building: BuildingListItem;
  loadingSummary: boolean;
  buildingSummary?: BuildingSummaryItem;
};

export const BuildingCard: FC<BuildingCardProps> = ({ t, building, buildingSummary, loadingSummary }) => {
  const buildingName = useMemo(() => building.name[i18n.language], [building.name]);

  const handleIconClick = useCallback(() => {
    if (building.id) {
      openPowerLogsDialog({
        buildingId: building.id,
        buildingName: buildingName,
        t,
      });
    }
  }, [building.id, buildingName, t]);

  const getBatteryIcon = (summary: BuildingSummaryItem): ReactNode | null => {
    const batteryPercent = summary.batteryPercent ?? 0;
    let icon: IconName | null;
    if (summary.isOffline) {
      return <span className="fa-layers fa-fw">
        <FontAwesomeIcon icon='battery-0' />
        <FontAwesomeIcon icon='slash' />
      </span>
    }
    if (batteryPercent > 75) {
      icon = 'battery-5';
    } else if (batteryPercent > 50) {
      icon = 'battery-4';
    } else if (batteryPercent > 25) {
      icon = 'battery-3';
    } else if (batteryPercent > 0) {
      icon = 'battery-2';
    } else {
      icon = 'battery-0';
    }
    return <FontAwesomeIcon icon={icon} />
  }

  const getGridIcon = (summary?: BuildingSummaryItem): ReactNode => {
    if (!summary) return <FontAwesomeIcon icon='lightbulb' />;
    
    return summary.isGridAvailable
      ? <FontAwesomeIcon icon='lightbulb' />
      : <span className="fa-layers fa-fw">
        <FontAwesomeIcon icon='lightbulb' />
        <FontAwesomeIcon icon='slash' />
      </span>;
  }

  const getHeaderGridIcon = (summary?: BuildingSummaryItem): ReactNode => {
    if (!summary) return <FontAwesomeIcon icon='lightbulb' />;

    if (summary.hasMixedReporterStates) {
      return <FontAwesomeIcon icon='lightbulb' style={{ color: 'white' }} />;
    }

    return summary.isGridAvailable
      ? <FontAwesomeIcon icon='lightbulb' />
      : <span className="fa-layers fa-fw">
        <FontAwesomeIcon icon='lightbulb' />
        <FontAwesomeIcon icon='slash' />
      </span>;
  }

  const getOperationIcon = (summary: BuildingSummaryItem): ReactNode | null => {
    if (summary.isCharging) {
      return <FontAwesomeIcon icon='arrow-trend-up' />;
    }
    if (summary.isDischarging) {
      return <FontAwesomeIcon icon='arrow-trend-down' />;
    }
    return <FontAwesomeIcon icon='pause' />;
  }

  const getOperationText = (summary: BuildingSummaryItem) => {
    if (!summary.isCharging && !summary.isDischarging) {
      return t('battery.idle');
    }
    if (summary.isCharging) {
      return t('battery.charging', { power: summary.chargePower ?? 0 });
    }
    return t('battery.discharging', { power: summary.consumptionPower });
  }

  const getChargeSourceText = (source: ChargeSource, t: TFunction) => {
    switch (source) {
      case ChargeSource.GRID:
        return t('battery.chargeSource.grid');
      case ChargeSource.SOLAR:
        return t('battery.chargeSource.solar');
      case ChargeSource.GENERATOR:
        return t('battery.chargeSource.generator');
      case ChargeSource.RECUPERATION:
        return t('battery.chargeSource.recuperation');
      default:
        return '';
    }
  };

  const rows = [];
  if (buildingSummary) {
    let availabilityText;
    switch (buildingSummary.gridAvailabilityPct) {
      case 0: availabilityText = t('grid.unavailable'); break;
      case 100: availabilityText = t('grid.available'); break;
      default: 
        availabilityText = buildingSummary.hasMixedReporterStates 
          ? `${t('grid.partiallyAvailable')} (${buildingSummary.gridAvailabilityPct}%)`
          : t('grid.partiallyAvailable');
        break;
    }
    rows.push({
      icon: getGridIcon(buildingSummary),
      left: t('grid.title') + ': ',
      right: availabilityText,
    });
  }
  if (building.hasBoundStation) {
    if (buildingSummary?.batteryPercent !== undefined && buildingSummary?.batteryPercent !== null) {
      rows.push({
        icon: getBatteryIcon(buildingSummary),
        left: <>{t('battery.title')}: </>,
        right: <>
            {!buildingSummary.isOffline && `${buildingSummary.batteryPercent}%`}
            {buildingSummary.isOffline && t('battery.offline')}
          </>,
      });
    }
    if (buildingSummary && !buildingSummary.isOffline) {
      const operationText = getOperationText(buildingSummary);

      rows.push({
        icon: getOperationIcon(buildingSummary),
        left: <>{t('operation.title')}: </>,
        right: <>{operationText || t('operation.idle')}</>,
      });
    }

    if (buildingSummary?.isCharging && !buildingSummary.isOffline) {
      rows.push({
        icon: <FontAwesomeIcon icon='plug' />,
        left: <>{t('battery.chargeSource.title')}: </>,
        right: <>{getChargeSourceText(buildingSummary.chargeSource, t)}</>,
      });
      rows.push({
        icon: <FontAwesomeIcon icon='clock' />,
        left: <>{t('timeTo.fullTitle')}: </>,
        right: <>{t('timeTo.fullValue', { timeToFull: buildingSummary?.batteryChargeTime })}</>,
      });
    }
    if (buildingSummary?.isDischarging && !buildingSummary.isOffline) {
      rows.push({
        icon: <FontAwesomeIcon icon='clock' />,
        left: <>{t('timeTo.emptyTitle')}: </>,
        right: <>{t('timeTo.emptyValue', { timeToEmpty: buildingSummary?.batteryDischargeTime })}</>,
      });
    }
  }

  const theme = useMantineTheme();

  const mixColors = (color1: string, color2: string, ratio: number) => {
    const c1 = parseInt(color1.slice(1), 16);
    const c2 = parseInt(color2.slice(1), 16);

    const r = (c1 >> 16) & 0xff;
    const g = (c1 >> 8) & 0xff;
    const b = c1 & 0xff;

    const r2 = (c2 >> 16) & 0xff;
    const g2 = (c2 >> 8) & 0xff;
    const b2 = c2 & 0xff;

    const mix = (a: number, b: number) => Math.round(a + (b - a) * ratio);

    return (
      "#" +
      ((1 << 24) + (mix(r, r2) << 16) + (mix(g, g2) << 8) + mix(b, b2))
        .toString(16)
        .slice(1)
    );
  }


  const getBatteryColor = useCallback((percentage: number) => {
    const value = Math.max(0, Math.min(percentage, 100));
    if (value <= 20) {
      return theme.colors.red[6];
    }
    if (value <= 50) {
      const ratio = (value - 20) / 30;
      return mixColors(theme.colors.red[5], theme.colors.yellow[5], ratio);
    }
    if (value <= 80) {
      const ratio = (value - 50) / 30;
      return mixColors(theme.colors.yellow[5], theme.colors.green[5], ratio);
    }
    return theme.colors.green[6];
  }, [theme]);


  const progress: ProgressProps | null = useMemo(() => {
    if (buildingSummary?.batteryPercent && !buildingSummary.isOffline) {
      return {
        value: buildingSummary.batteryPercent,
        striped: true,
        animated: buildingSummary.isCharging || buildingSummary.isDischarging,
        color: getBatteryColor(buildingSummary.batteryPercent),
      } as ProgressProps;
    }
    return null;
  }, [buildingSummary, getBatteryColor]);

  const isChristmas = useMemo(() => isChristmasSeason(), []);

  return (
    <StatsCard
      christmasTree={isChristmas}
      loading={loadingSummary}
      key={`building_${building.id}`}
      title={buildingName}
      bgColor={building.color}
      icon={getHeaderGridIcon(buildingSummary)}
      iconColor={
        buildingSummary?.hasMixedReporterStates 
          ? "yellow.6" 
          : buildingSummary?.isGridAvailable 
            ? "green.9" 
            : "red.9"
      }
      onClick={handleIconClick}
      rows={rows}
      progress={progress}
    >
    </StatsCard>
  );
}