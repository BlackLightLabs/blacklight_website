import { useEffect } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

/**
 * OAuth Success Page
 *
 * This page is the redirect_url for OAuth flows.
 * After successful OAuth authentication, the backend redirects here.
 * The httpOnly auth cookie has already been set by the backend.
 *
 * This component simply:
 * 1. Shows a success message
 * 2. Invalidates the user query to fetch fresh user data
 * 3. Redirects to the home page
 */
export default function OAuthSuccess() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  useEffect(() => {
    // Show success toast
    toast.success("Successfully logged in!");

    // Invalidate user query to fetch fresh user data (now with auth cookie)
    queryClient.invalidateQueries({ queryKey: ["user"] });

    // Redirect to home page after a short delay
    const timer = setTimeout(() => {
      navigate("/", { replace: true });
    }, 1000);

    return () => clearTimeout(timer);
  }, [navigate, queryClient]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">Successfully logged in!</h1>
        <p className="text-muted-foreground mt-2">Redirecting you to the app...</p>
      </div>
    </div>
  );
}
