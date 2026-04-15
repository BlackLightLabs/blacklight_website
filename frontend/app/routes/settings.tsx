import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { ModeToggle } from "../components/mode-toggle";
import { useTheme } from "../components/theme-provider";
import { useMySettings, useUpdateMySettings, useUpdateTheme } from "../hooks/use-settings";
import { type SettingsUpdate } from "../lib/settings-api";
import { authApi } from "../lib/auth-api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { toast } from "sonner";
import { Loader2, Link as LinkIcon, Unlink } from "lucide-react";

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const { data: settings, isLoading } = useMySettings();
  const updateSettingsMutation = useUpdateMySettings();
  const updateThemeMutation = useUpdateTheme();
  const [systemPrompt, setSystemPrompt] = useState("");
  const [agentInstructions, setAgentInstructions] = useState("");
  const queryClient = useQueryClient();

  // Fetch connected OAuth accounts
  const { data: connectedAccounts, isLoading: isLoadingAccounts } = useQuery({
    queryKey: ["connected-oauth-accounts"],
    queryFn: () => authApi.getConnectedAccounts(),
  });

  // Disconnect OAuth account mutation
  const disconnectMutation = useMutation({
    mutationFn: (accountId: number) => authApi.disconnectOAuthAccount(accountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connected-oauth-accounts"] });
      toast.success("OAuth account disconnected successfully");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to disconnect account");
    },
  });

  // Sync form state with loaded settings
  useEffect(() => {
    if (settings) {
      // Sync local theme with server theme
      if (settings.theme && settings.theme !== theme) {
        setTheme(settings.theme);
      }

      // Load custom prompts if they exist
      if (settings.custom_prompts) {
        setSystemPrompt(settings.custom_prompts.system_prompt || "");
        setAgentInstructions(settings.custom_prompts.agent_instructions || "");
      }
    }
  }, [settings, theme, setTheme]);

  const handleThemeChange = async (newTheme: "light" | "dark" | "system") => {
    try {
      // Optimistically update UI
      const previousTheme = theme;
      setTheme(newTheme);

      // Sync to server
      await updateThemeMutation.mutateAsync(newTheme);
      toast.success("Theme updated successfully");
    } catch (error) {
      console.error("Failed to update theme:", error);
      toast.error("Failed to update theme");
      // Revert on error
      if (settings) {
        setTheme(settings.theme);
      }
    }
  };

  const handleSavePrompts = async () => {
    try {
      const update: SettingsUpdate = {
        custom_prompts: {
          system_prompt: systemPrompt,
          agent_instructions: agentInstructions,
        },
      };

      await updateSettingsMutation.mutateAsync(update);
      toast.success("Custom prompts saved successfully");
    } catch (error) {
      console.error("Failed to save prompts:", error);
      toast.error("Failed to save custom prompts");
    }
  };

  if (isLoading) {
    return (
      <ProtectedRoute>
        <div className="container mx-auto flex min-h-[400px] items-center justify-center p-6">
          <Loader2 className="text-muted-foreground h-8 w-8 animate-spin" />
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="container mx-auto max-w-4xl p-6">
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold">Settings</h1>
            <p className="text-muted-foreground mt-2">
              Manage your account preferences and customize your agent builder experience.
            </p>
          </div>

          {/* Appearance Settings */}
          <Card>
            <CardHeader>
              <CardTitle>Appearance</CardTitle>
              <CardDescription>Customize how the agent builder looks for you.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Theme</Label>
                  <p className="text-muted-foreground text-sm">
                    Choose your preferred theme or use system preference
                  </p>
                </div>
                <ModeToggle />
              </div>

              <div className="border-t pt-4">
                <div className="flex gap-2">
                  <Button
                    variant={theme === "light" ? "default" : "outline"}
                    onClick={() => handleThemeChange("light")}
                    className="flex-1"
                  >
                    Light
                  </Button>
                  <Button
                    variant={theme === "dark" ? "default" : "outline"}
                    onClick={() => handleThemeChange("dark")}
                    className="flex-1"
                  >
                    Dark
                  </Button>
                  <Button
                    variant={theme === "system" ? "default" : "outline"}
                    onClick={() => handleThemeChange("system")}
                    className="flex-1"
                  >
                    System
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Custom Prompts */}
          <Card>
            <CardHeader>
              <CardTitle>Custom Prompts</CardTitle>
              <CardDescription>
                Override default prompts used when creating agents. Leave blank to use defaults.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="system-prompt">System Prompt</Label>
                <Textarea
                  id="system-prompt"
                  placeholder="Enter custom system prompt for agent creation..."
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  rows={4}
                  className="font-mono text-sm"
                />
                <p className="text-muted-foreground text-xs">
                  This prompt guides the AI when helping you create new agents.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="agent-instructions">Default Agent Instructions</Label>
                <Textarea
                  id="agent-instructions"
                  placeholder="Enter default instructions for new agents..."
                  value={agentInstructions}
                  onChange={(e) => setAgentInstructions(e.target.value)}
                  rows={4}
                  className="font-mono text-sm"
                />
                <p className="text-muted-foreground text-xs">
                  These instructions are used as a starting point for new agents.
                </p>
              </div>

              <div className="flex justify-end">
                <Button onClick={handleSavePrompts} disabled={updateSettingsMutation.isPending}>
                  {updateSettingsMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Save Prompts
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Connected Accounts */}
          <Card>
            <CardHeader>
              <CardTitle>Connected Accounts</CardTitle>
              <CardDescription>
                Manage your OAuth provider connections. You can link multiple accounts for easier login.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoadingAccounts ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
                </div>
              ) : (
                <>
                  {/* Connected Accounts List */}
                  {connectedAccounts && connectedAccounts.accounts.length > 0 ? (
                    <div className="space-y-3">
                      <Label>Connected Providers</Label>
                      {connectedAccounts.accounts.map((account) => (
                        <div
                          key={account.id}
                          className="border-border flex items-center justify-between rounded-lg border p-4"
                        >
                          <div className="flex items-center gap-3">
                            <LinkIcon className="text-muted-foreground h-5 w-5" />
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-medium">{account.display_name}</span>
                                <Badge variant="secondary">Connected</Badge>
                              </div>
                              <p className="text-muted-foreground text-sm">{account.account_email}</p>
                              <p className="text-muted-foreground text-xs">
                                Connected {new Date(account.connected_at).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => disconnectMutation.mutate(account.id)}
                            disabled={disconnectMutation.isPending}
                          >
                            {disconnectMutation.isPending ? (
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <Unlink className="mr-2 h-4 w-4" />
                            )}
                            Disconnect
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-muted-foreground text-center text-sm">
                      No OAuth accounts connected yet.
                    </div>
                  )}

                  {/* Available Providers to Connect */}
                  {connectedAccounts && connectedAccounts.available_providers.length > 0 && (
                    <>
                      {connectedAccounts.accounts.length > 0 && (
                        <Separator className="my-4" />
                      )}
                      <div className="space-y-3">
                        <Label>Available Providers</Label>
                        <p className="text-muted-foreground text-sm">
                          Connect additional providers for more login options.
                        </p>
                        {connectedAccounts.available_providers.map((provider) => (
                          <div
                            key={provider.name}
                            className="border-border flex items-center justify-between rounded-lg border p-4"
                          >
                            <div className="flex items-center gap-3">
                              <LinkIcon className="text-muted-foreground h-5 w-5" />
                              <div>
                                <span className="font-medium">{provider.display_name}</span>
                                <p className="text-muted-foreground text-sm">Not connected</p>
                              </div>
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => authApi.initiateOAuthLogin(provider.name)}
                            >
                              <LinkIcon className="mr-2 h-4 w-4" />
                              Connect
                            </Button>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  );
}
