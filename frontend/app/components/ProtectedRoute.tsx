/**
 * Protected Route Component
 *
 * Wraps routes that require authentication.
 * Redirects to login if user is not authenticated.
 */

import { Navigate } from "react-router";
import { useCurrentUser } from "~/hooks/use-auth";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermission?: string;
}

export function ProtectedRoute({ children, requiredPermission }: ProtectedRouteProps) {
  const { data: user, isLoading } = useCurrentUser();

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="border-primary h-12 w-12 animate-spin rounded-full border-b-2"></div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // TODO: Add permission checking when needed
  // if (requiredPermission && !hasPermission(user, requiredPermission)) {
  //   return <Navigate to="/unauthorized" replace />;
  // }

  return <>{children}</>;
}
