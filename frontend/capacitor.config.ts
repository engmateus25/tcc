import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'br.com.aquamonitor.app',
  appName: 'AquaMonitor',
  webDir: 'dist',


  android: {
    allowMixedContent: true,
  },

  server: {
    cleartext: true,
  },
};

export default config;
