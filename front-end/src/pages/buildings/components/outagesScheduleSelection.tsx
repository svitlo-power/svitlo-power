import { FC, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Button,
  Group,
  Loader,
  Select,
  Stack,
  Stepper,
  Text,
} from "@mantine/core";
import { TFunction } from "i18next";
import { OutagesScheduleConfig } from "../../../schemas/dashboardEdit";
import { getErrorMessage } from "../../../utils";
import apiClient from "../../../utils/apiClient";
import {
  LEGACY_YASNO_PROVIDER_ID,
  LEGACY_YASNO_PROVIDER_NAME,
  LEGACY_YASNO_REGION_ID,
  LEGACY_YASNO_REGION_NAME,
} from "../../../constants/outagesSchedule";

type RegionOption = {
  id: number;
  value: string;
  label: string;
};

type ProviderOption = {
  id: number;
  name: string;
};

const matchesIdOrLegacyName = (
  savedValue: number | string | null,
  id: number,
  legacyName: string,
) =>
  savedValue === id || savedValue === String(id) || savedValue === legacyName;

type OutagesScheduleSelectionProps = {
  value: OutagesScheduleConfig;
  t: TFunction;
  onChange: (value: Partial<OutagesScheduleConfig>) => void;
};

export const OutagesScheduleSelection: FC<OutagesScheduleSelectionProps> = ({
  value,
  t,
  onChange,
}) => {
  const { regionId, dsoId, queue } = value;
  const [regions, setRegions] = useState<RegionOption[]>([]);
  const [providers, setProviders] = useState<ProviderOption[]>([]);
  const [queues, setQueues] = useState<string[]>([]);
  const [step, setStep] = useState(0);
  const [loadingRegions, setLoadingRegions] = useState(true);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [loadingQueues, setLoadingQueues] = useState(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const currentValue = useRef(value);
  const onChangeRef = useRef(onChange);
  const translateRef = useRef(t);

  useEffect(() => {
    currentValue.current = value;
    onChangeRef.current = onChange;
    translateRef.current = t;
  }, [onChange, t, value]);

  const selectedRegion = useMemo(
    () =>
      regions.find((item) =>
        matchesIdOrLegacyName(regionId, item.id, item.value),
      ),
    [regions, regionId],
  );
  const selectedProvider = useMemo(
    () =>
      providers.find((item) =>
        matchesIdOrLegacyName(dsoId, item.id, item.name),
      ),
    [providers, dsoId],
  );
  useEffect(() => {
    let active = true;
    apiClient
      .get<RegionOption[]>("/outagesSchedule/regions")
      .then(({ data }) => {
        if (!active) return;
        setRegions(data);
        const currentRegion = currentValue.current.regionId;
        if (currentRegion) {
          const savedRegion =
            data.find((item) =>
              matchesIdOrLegacyName(currentRegion, item.id, item.value),
            ) ??
            (currentRegion === LEGACY_YASNO_REGION_NAME
              ? data.find((item) => item.id === LEGACY_YASNO_REGION_ID)
              : undefined);
          if (savedRegion) {
            if (savedRegion.id !== currentRegion) {
              onChangeRef.current({ regionId: savedRegion.id });
            }
            setLoadingProviders(true);
            setStep(
              currentValue.current.dsoId && currentValue.current.queue ? 2 : 1,
            );
          }
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setDiscoveryError(
            getErrorMessage(error) ||
              translateRef.current("dashboardEdit.discoveryError"),
          );
        }
      })
      .finally(() => {
        if (active) setLoadingRegions(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const selectedRegionValue = selectedRegion?.value;
  useEffect(() => {
    if (!selectedRegionValue) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setProviders([]);
      setLoadingProviders(false);
      return;
    }
    let active = true;
    setLoadingProviders(true);
    apiClient
      .get<ProviderOption[]>(
        `/outagesSchedule/providers/${encodeURIComponent(selectedRegionValue)}`,
      )
      .then(({ data }) => {
        if (!active) return;
        setProviders(data);
        const currentDso = currentValue.current.dsoId;
        const nextProvider =
          data.find((provider) =>
            matchesIdOrLegacyName(currentDso, provider.id, provider.name),
          ) ??
          (currentDso === LEGACY_YASNO_PROVIDER_NAME
            ? data.find((provider) => provider.id === LEGACY_YASNO_PROVIDER_ID)
            : undefined) ??
          (!currentDso && data.length === 1 ? data[0] : undefined);
        if (nextProvider) {
          if (nextProvider.id !== currentDso) {
            onChangeRef.current({ dsoId: nextProvider.id });
          }
          setLoadingQueues(true);
          if (data.length === 1) setStep(2);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setDiscoveryError(
            getErrorMessage(error) ||
              translateRef.current("dashboardEdit.discoveryError"),
          );
        }
      })
      .finally(() => {
        if (active) setLoadingProviders(false);
      });
    return () => {
      active = false;
    };
  }, [selectedRegionValue]);

  const selectedRegionId = selectedRegion?.id;
  const selectedProviderId = selectedProvider?.id;
  useEffect(() => {
    if (selectedRegionId === undefined || selectedProviderId === undefined) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setQueues([]);
      setLoadingQueues(false);
      return;
    }
    let active = true;
    setLoadingQueues(true);
    apiClient
      .get<string[]>(
        `/outagesSchedule/queues/${selectedRegionId}/${selectedProviderId}`,
      )
      .then(({ data }) => {
        if (!active) return;
        setQueues(data);
        const currentQueue = currentValue.current.queue;
        if (currentQueue && !data.includes(currentQueue)) {
          onChangeRef.current({ queue: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setDiscoveryError(
            getErrorMessage(error) ||
              translateRef.current("dashboardEdit.discoveryError"),
          );
        }
      })
      .finally(() => {
        if (active) setLoadingQueues(false);
      });
    return () => {
      active = false;
    };
  }, [selectedProviderId, selectedRegionId]);

  const handleRegionChange = (regionIdValue: string | null) => {
    const regionId = regionIdValue === null ? null : Number(regionIdValue);
    onChange({
      regionId,
      dsoId: null,
      queue: null,
    });
    setLoadingProviders(regionId !== null);
    setLoadingQueues(false);
    setProviders([]);
    setQueues([]);
    setStep((currentStep) => (currentStep === 2 ? 1 : currentStep));
  };

  const handleProviderChange = (providerIdValue: string | null) => {
    const dsoId = providerIdValue === null ? null : Number(providerIdValue);
    onChange({
      dsoId,
      queue: null,
    });
    setLoadingQueues(dsoId !== null);
    setQueues([]);
    setStep(2);
  };

  return (
    <Stack>
      {loadingRegions ? (
        <Group justify="center" py="xl">
          <Loader size="sm" />
          <Text>{t("dashboardEdit.loading")}</Text>
        </Group>
      ) : (
        <Stepper
          active={step}
          onStepClick={setStep}
          allowNextStepsSelect={false}
          size="xs"
          iconSize={16}
        >
          <Stepper.Step label={t("dashboardEdit.region")}>
            <Select
              label={t("dashboardEdit.region")}
              placeholder={t("dashboardEdit.selectRegion")}
              data={regions.map((item) => ({
                value: String(item.id),
                label: item.label,
              }))}
              value={selectedRegion ? String(selectedRegion.id) : null}
              onChange={handleRegionChange}
              searchable
            />
            <Group justify="flex-end" mt="xs">
              <Button
                onClick={() => setStep(1)}
                disabled={!regionId || loadingProviders}
                loading={loadingProviders}
              >
                {t("button.next")}
              </Button>
            </Group>
          </Stepper.Step>
          <Stepper.Step label={t("dashboardEdit.provider")}>
            <Stack gap="xs">
              <Select
                label={t("dashboardEdit.provider")}
                placeholder={t("dashboardEdit.selectProvider")}
                data={providers.map((provider) => ({
                  value: String(provider.id),
                  label: provider.name,
                }))}
                value={selectedProvider ? String(selectedProvider.id) : null}
                onChange={handleProviderChange}
                disabled={loadingProviders || !selectedRegion}
                rightSection={
                  loadingProviders ? <Loader size="xs" /> : undefined
                }
              />
              <Group justify="space-between">
                <Button variant="default" onClick={() => setStep(0)}>
                  {t("button.back")}
                </Button>
                <Button onClick={() => setStep(2)} disabled={!dsoId}>
                  {t("button.next")}
                </Button>
              </Group>
            </Stack>
          </Stepper.Step>
          <Stepper.Step label={t("dashboardEdit.queue")}>
            <Stack gap="xs">
              <Select
                label={t("dashboardEdit.queue")}
                placeholder={t("dashboardEdit.selectQueue")}
                data={queues}
                value={queue}
                onChange={(queue) => onChange({ queue })}
                disabled={loadingQueues || !selectedProvider}
                rightSection={loadingQueues ? <Loader size="xs" /> : undefined}
              />
              <Text size="sm" c="dimmed">
                {t("dashboardEdit.selectionSummary", {
                  region: selectedRegion?.label || "-",
                  provider: selectedProvider?.name || "-",
                  queue: queue || "-",
                })}
              </Text>
              <Group justify="space-between">
                <Button variant="default" onClick={() => setStep(1)}>
                  {t("button.back")}
                </Button>
              </Group>
            </Stack>
          </Stepper.Step>
          <Stepper.Completed>{null}</Stepper.Completed>
        </Stepper>
      )}
      {discoveryError && <Alert color="red">{discoveryError}</Alert>}
    </Stack>
  );
};
