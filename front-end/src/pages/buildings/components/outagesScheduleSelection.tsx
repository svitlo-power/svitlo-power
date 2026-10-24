import { FC, useEffect, useMemo, useState } from "react";
import { Alert, Button, Group, Loader, Select, Stack, Stepper, Text } from "@mantine/core";
import { TFunction } from "i18next";
import { OutagesScheduleConfig } from "../../../schemas/dashboardEdit";
import { getErrorMessage } from "../../../utils";
import apiClient from "../../../utils/apiClient";

type RegionOption = {
  id: number;
  value: string;
  label: string;
};

type ProviderOption = {
  id: number;
  name: string;
};

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
  const { region, dso, queue } = value;
  const [regions, setRegions] = useState<RegionOption[]>([]);
  const [providers, setProviders] = useState<ProviderOption[]>([]);
  const [queues, setQueues] = useState<string[]>([]);
  const [step, setStep] = useState(0);
  const [loadingRegions, setLoadingRegions] = useState(true);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [loadingQueues, setLoadingQueues] = useState(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);

  const selectedRegion = useMemo(
    () => regions.find((item) => item.value === region),
    [regions, region],
  );
  const selectedProvider = useMemo(
    () => providers.find((item) => item.name === dso),
    [providers, dso],
  );
  const matchesInitialRegion = Boolean(
    selectedRegion
    && (
      selectedRegion.value === region
      || (region === 'Kyiv' && selectedRegion.id === 25)
    ),
  );
  const matchesInitialProvider = Boolean(
    selectedProvider
    && (
      selectedProvider.name === dso
      || (dso === 'Yasno' && selectedProvider.id === 902)
    ),
  );

  useEffect(() => {
    let active = true;
    apiClient.get<RegionOption[]>('/outagesSchedule/regions')
      .then(({ data }) => {
        if (!active) return;
        setRegions(data);
        if (region) {
          const savedRegion = data.find((item) => item.value === region)
            ?? (region === 'Kyiv' ? data.find((item) => item.id === 25) : undefined);
          if (savedRegion) {
            if (savedRegion.value !== region) {
              onChange({ region: savedRegion.value });
            }
            setLoadingProviders(true);
            setStep(dso && queue ? 2 : 1);
          }
        }
      })
      .catch((error: unknown) => {
        if (active) setDiscoveryError(getErrorMessage(error) || t('dashboardEdit.discoveryError'));
      })
      .finally(() => {
        if (active) setLoadingRegions(false);
      });
    return () => {
      active = false;
    };
  // This effect initializes available regions and the initial step when the dialog opens.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedRegion) return;
    let active = true;
    apiClient.get<ProviderOption[]>(
      `/outagesSchedule/providers/${encodeURIComponent(selectedRegion.value)}`,
    )
      .then(({ data }) => {
        if (!active) return;
        setProviders(data);
        const savedProvider = matchesInitialRegion
          ? data.find((provider) => provider.name === dso)
            ?? (dso === 'Yasno' ? data.find((provider) => provider.id === 902) : undefined)
          : undefined;
        const nextProvider = savedProvider ?? (data.length === 1 ? data[0] : undefined);
        if (nextProvider) {
          if (nextProvider.name !== dso) {
            onChange({ dso: nextProvider.name });
          }
          setLoadingQueues(true);
          if (data.length === 1) setStep(2);
        }
      })
      .catch((error: unknown) => {
        if (active) setDiscoveryError(getErrorMessage(error) || t('dashboardEdit.discoveryError'));
      })
      .finally(() => {
        if (active) setLoadingProviders(false);
      });
    return () => {
      active = false;
    };
  }, [dso, matchesInitialRegion, onChange, region, selectedRegion, t]);

  useEffect(() => {
    if (!selectedRegion || !selectedProvider) return;
    let active = true;
    apiClient.get<string[]>(
      `/outagesSchedule/queues/${selectedRegion.id}/${selectedProvider.id}`,
    )
      .then(({ data }) => {
        if (!active) return;
        setQueues(data);
        if (matchesInitialRegion && matchesInitialProvider && queue && !data.includes(queue)) {
          onChange({ queue: null });
        }
      })
      .catch((error: unknown) => {
        if (active) setDiscoveryError(getErrorMessage(error) || t('dashboardEdit.discoveryError'));
      })
      .finally(() => {
        if (active) setLoadingQueues(false);
      });
    return () => {
      active = false;
    };
  }, [
    matchesInitialProvider,
    matchesInitialRegion,
    onChange,
    selectedProvider,
    selectedRegion,
    queue,
    region,
    t,
  ]);

  const handleRegionChange = (regionName: string | null) => {
    onChange({
      region: regionName,
      dso: null,
      queue: null,
    });
    setLoadingProviders(Boolean(regionName));
    setLoadingQueues(false);
    setProviders([]);
    setQueues([]);
    setStep(1);
  };

  const handleProviderChange = (providerName: string | null) => {
    onChange({
      dso: providerName,
      queue: null,
    });
    setLoadingQueues(Boolean(providerName));
    setQueues([]);
    setStep(2);
  };

  return (
    <Stack>
      {loadingRegions ? (
        <Group justify="center" py="xl">
          <Loader size="sm" />
          <Text>{t('dashboardEdit.loading')}</Text>
        </Group>
      ) : (
      <Stepper
        active={step}
        onStepClick={setStep}
        allowNextStepsSelect={false}
        size="xs"
        iconSize={16}
      >
        <Stepper.Step label={t('dashboardEdit.region')}>
          <Select
            label={t('dashboardEdit.region')}
            placeholder={t('dashboardEdit.selectRegion')}
            data={regions}
            value={region}
            onChange={handleRegionChange}
            searchable
          />
        </Stepper.Step>
        <Stepper.Step label={t('dashboardEdit.provider')}>
          <Stack gap="xs">
            <Select
              label={t('dashboardEdit.provider')}
              placeholder={t('dashboardEdit.selectProvider')}
              data={providers.map((provider) => ({ value: provider.name, label: provider.name }))}
              value={dso}
              onChange={handleProviderChange}
              disabled={loadingProviders || !selectedRegion}
              rightSection={loadingProviders ? <Loader size="xs" /> : undefined}
            />
            <Group justify="space-between">
              <Button variant="default" onClick={() => setStep(0)}>{t('button.back')}</Button>
              <Button onClick={() => setStep(2)} disabled={!dso}>{t('button.next')}</Button>
            </Group>
          </Stack>
        </Stepper.Step>
        <Stepper.Step label={t('dashboardEdit.queue')}>
          <Stack gap="xs">
            <Select
              label={t('dashboardEdit.queue')}
              placeholder={t('dashboardEdit.selectQueue')}
              data={queues}
              value={queue}
              onChange={(queue) => onChange({ queue })}
              disabled={loadingQueues || !selectedProvider}
              rightSection={loadingQueues ? <Loader size="xs" /> : undefined}
            />
            <Text size="sm" c="dimmed">
              {t('dashboardEdit.selectionSummary', {
                region: region || '-',
                provider: dso || '-',
                queue: queue || '-',
              })}
            </Text>
            <Group justify="space-between">
              <Button variant="default" onClick={() => setStep(1)}>{t('button.back')}</Button>
            </Group>
          </Stack>
        </Stepper.Step>
        <Stepper.Completed>{null}</Stepper.Completed>
      </Stepper>
      )}
      {step === 0 && <Group justify="flex-end">
        {!loadingRegions && <Button onClick={() => setStep(1)} disabled={!region}>{t('button.next')}</Button>}
      </Group>}
      {discoveryError && <Alert color="red">{discoveryError}</Alert>}
    </Stack>
  );
};
