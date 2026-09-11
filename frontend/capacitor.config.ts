import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.maxwell.accounting',
  appName: 'Maxwell Accounting',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
    cleartext: false,
  },
  android: {
    minSdkVersion: 24,
    targetSdkVersion: 34,
  },
};

export default config;
