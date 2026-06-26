import { defineConfig } from "@playwright/test";
import baseConfig from "./playwright.config";

export default defineConfig({
  ...baseConfig,
  projects: (baseConfig.projects ?? []).map((project) => ({
    ...project,
    use: {
      ...(project.use ?? {}),
      launchOptions: {
        ...((project.use as { launchOptions?: Record<string, unknown> })?.launchOptions ??
          {}),
        slowMo: 500,
      },
    },
  })),
});
