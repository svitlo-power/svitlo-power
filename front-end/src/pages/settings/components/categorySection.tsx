import { useTranslation } from "react-i18next";
import { Setting, SystemSettingValue } from "../../../stores/types/settings";
import SettingsRenderer from "../../../components/settingsRenderer";
import { Accordion, SimpleGrid } from "@mantine/core";

interface CategorySectionProps {
  category: string;
  settings: Setting[];
  onUpdate: (key: string, value: SystemSettingValue) => void;
}

export const CategorySection: React.FC<CategorySectionProps> = ({
  category,
  settings,
  onUpdate,
}) => {
  const { t } = useTranslation();

  const categoryLabel = t(`settings.categories.${category}`) || category;

  return (
    <Accordion.Item key={category} value={category}>
      <Accordion.Control value={category}>{categoryLabel}</Accordion.Control>
      <Accordion.Panel>
        <SimpleGrid cols={{ md: 2, sm: 1}}>
          {settings.map((setting) => (
            <SettingsRenderer
              key={setting.key}
              setting={setting}
              onChange={onUpdate}
            />
          ))}
        </SimpleGrid>
      </Accordion.Panel>
    </Accordion.Item>);
};
