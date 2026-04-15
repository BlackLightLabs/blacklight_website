import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { settingsApi, type UserSettings, type SettingsUpdate } from "~/lib/settings-api";

export const settingsKeys = {
  mySettings: ["settings", "me"] as const,
};

/**
 * Hook to get current user's settings
 */
export function useMySettings() {
  return useQuery({
    queryKey: settingsKeys.mySettings,
    queryFn: settingsApi.getMySettings,
    retry: false,
  });
}

/**
 * Hook to update current user's settings
 */
export function useUpdateMySettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (settings: SettingsUpdate) => settingsApi.updateMySettings(settings),
    onSuccess: (data) => {
      // Update cached settings
      queryClient.setQueryData(settingsKeys.mySettings, data);
    },
  });
}

/**
 * Hook to update theme preference
 */
export function useUpdateTheme() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (theme: "light" | "dark" | "system") => settingsApi.updateTheme(theme),
    onSuccess: (data) => {
      // Update cached settings
      queryClient.setQueryData(settingsKeys.mySettings, data);
    },
  });
}
