import { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { LocalizableValue } from "../schemas";
import { AVAILABLE_LANGUAGES } from "../i18n";

export function usePageTranslation(pageName: string): TFunction {
  return useTranslation([pageName, 'common'], { nsMode: "fallback" }).t;
}

const langCountryMap: Record<string, string> = {
  'uk': 'ua',
  'en': 'gb',
  'cimode': 'al',
};

export function getCountryByLang(lang: string): string {
  return langCountryMap[lang];
}

export const localizableValueToString = (
  value: LocalizableValue
): string => {
  return AVAILABLE_LANGUAGES
    .map(lang => `'${value[lang]}'`)
    .join('/');
};