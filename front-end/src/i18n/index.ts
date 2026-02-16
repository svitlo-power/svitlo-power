import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import enCommon from './en/common.json';
import ukCommon from './uk/common.json';
import enDashboard from './en/dashboard.json';
import ukDashboard from './uk/dashboard.json';
import enBots from './en/bots.json';
import ukBots from './uk/bots.json';
import enStations from './en/stations.json';
import ukStations from './uk/stations.json';
import enChats from './en/chats.json';
import ukChats from './uk/chats.json';
import enExtData from './en/extData.json';
import ukExtData from './uk/extData.json';
import enUsers from './en/users.json';
import ukUsers from './uk/users.json';
import enHome from './en/home.json';
import ukHome from './uk/home.json';
import enMessages from './en/messages.json';
import ukMessages from './uk/messages.json';
import enDevices from './en/devices.json';
import ukDevices from './uk/devices.json';

export const AVAILABLE_LANGUAGES = ['en', 'uk'];

i18n
  .use(initReactI18next)
  .use(LanguageDetector)
  .init({
    fallbackLng: 'en',
    lng: localStorage.getItem('lang') || 'en',

    ns: ['common'],
    defaultNS: 'common',

    resources: {
      en: {
        common: enCommon,
        dashboard: enDashboard,
        bots: enBots,
        stations: enStations,
        chats: enChats,
        extData: enExtData,
        users: enUsers,
        home: enHome,
        messages: enMessages,
        devices: enDevices,
      },
      uk: {
        common: ukCommon,
        dashboard: ukDashboard,
        bots: ukBots,
        stations: ukStations,
        chats: ukChats,
        extData: ukExtData,
        users: ukUsers,
        home: ukHome,
        messages: ukMessages,
        devices: ukDevices,
      },
    },

    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
