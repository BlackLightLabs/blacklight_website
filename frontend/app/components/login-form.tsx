import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { cn } from "~/lib/utils";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "~/components/ui/field";
import { Input } from "~/components/ui/input";
import { Separator } from "~/components/ui/separator";
import { useLogin } from "~/hooks/use-auth";
import { authApi } from "~/lib/auth-api";
import { OAuthButton } from "~/components/oauth-button";

export function LoginForm({ className, ...props }: React.ComponentProps<"div">) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const loginMutation = useLogin();
  const navigate = useNavigate();

  // Fetch OAuth providers
  const { data: oauthProviders } = useQuery({
    queryKey: ["oauth-providers"],
    queryFn: () => authApi.getOAuthProviders(),
  });

  const enabledProviders = oauthProviders?.providers.filter((p) => p.enabled) || [];
  const showOAuth = oauthProviders?.enabled && enabledProviders.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await loginMutation.mutateAsync({ email, password });
      toast.success("Welcome back!");
      navigate("/");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Login failed");
    }
  };

  const handleOAuthLogin = async (provider: string) => {
    try {
      await authApi.initiateOAuthLogin(provider);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to initiate OAuth login");
    }
  };

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Welcome back</CardTitle>
          <CardDescription>
            {showOAuth ? "Login with your account" : "Login with your email and password"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* OAuth Buttons */}
          {showOAuth && (
            <>
              <div className="space-y-2">
                {enabledProviders.map((provider) => (
                  <OAuthButton
                    key={provider.name}
                    provider={provider.name}
                    displayName={provider.display_name}
                    onClick={() => handleOAuthLogin(provider.name)}
                  />
                ))}
              </div>

              <div className="relative my-4">
                <Separator />
                <span className="bg-background text-muted-foreground absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 px-2 text-xs">
                  Or continue with
                </span>
              </div>
            </>
          )}

          {/* Email/Password Form */}
          <form onSubmit={handleSubmit}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="email">Email</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  placeholder="m@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </Field>
              <Field>
                <div className="flex items-center">
                  <FieldLabel htmlFor="password">Password</FieldLabel>
                </div>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </Field>
              <Field>
                <Button type="submit" disabled={loginMutation.isPending}>
                  {loginMutation.isPending ? "Logging in..." : "Login"}
                </Button>
                <FieldDescription className="text-center">
                  Don&apos;t have an account?{" "}
                  <Link to="/signup" className="underline">
                    Sign up
                  </Link>
                </FieldDescription>
              </Field>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
      <FieldDescription className="px-6 text-center">
        By clicking continue, you agree to our{" "}
        <Link to="/terms" className="underline">
          Terms of Service
        </Link>{" "}
        and{" "}
        <Link to="/privacy" className="underline">
          Privacy Policy
        </Link>
        .
      </FieldDescription>
    </div>
  );
}
