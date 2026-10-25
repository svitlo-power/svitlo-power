import { useTranslation } from "react-i18next";
import { Setting, SystemSettingValue } from "../../../stores/types/settings";
import SettingsRenderer from "../../../components/settingsRenderer";
import { Accordion, Card, SimpleGrid } from "@mantine/core";
import { SettingCategory } from "../../../stores/types/settings";
import { getLocalizedValue } from "../../../utils/i18n";

interface CategorySectionProps {
  category: SettingCategory;
  settings: Setting[];
  onUpdate: (key: string, value: SystemSettingValue) => void;
}

export const CategorySection: React.FC<CategorySectionProps> = ({
  category,
  settings,
  onUpdate,
}) => {
  const { i18n } = useTranslation();

  const categoryLabel = getLocalizedValue(
    category.label,
    i18n.resolvedLanguage ?? i18n.language,
  );

  return (
    <Accordion.Item key={category.id} value={category.id}>
      <Accordion.Control value={category.id}>{categoryLabel}</Accordion.Control>
      <Accordion.Panel>
        <SimpleGrid cols={{ md: 2, sm: 1}}>
          {settings.map((setting) => (
            <Card key={setting.key} shadow="sm" padding="sm" withBorder>
              <SettingsRenderer
                setting={setting}
                onChange={onUpdate}
              />
            </Card>
          ))}
        </SimpleGrid>
      </Accordion.Panel>
    </Accordion.Item>);
};
