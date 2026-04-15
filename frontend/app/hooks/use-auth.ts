import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi, type User } from "~/lib/auth-api";

export const authKeys = {
  currentUser: ["auth", "currentUser"] as const,
};

/**
 * Hook to get the current authenticated user
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: authKeys.currentUser,
    queryFn: authApi.getCurrentUser,
    retry: false,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Hook to login
 */
export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: async () => {
      // Refetch current user after login
      await queryClient.invalidateQueries({ queryKey: authKeys.currentUser });
    },
  });
}

/**
 * Hook to register
 */
export function useRegister() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      email,
      password,
      full_name,
    }: {
      email: string;
      password: string;
      full_name?: string;
    }) => {
      // Register the user
      const user = await authApi.register({ email, password, full_name });
      // Auto-login after registration
      await authApi.login(email, password);
      return user;
    },
    onSuccess: async () => {
      // Refetch current user after registration and login
      await queryClient.invalidateQueries({ queryKey: authKeys.currentUser });
    },
  });
}

/**
 * Hook to logout
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      // Clear user data from cache
      queryClient.setQueryData(authKeys.currentUser, null);
      queryClient.clear();
    },
  });
}

/**
 * Combined auth hook for convenience
 */
export function useAuth() {
  const { data: user, isLoading, error } = useCurrentUser();
  const login = useLogin();
  const logout = useLogout();
  const register = useRegister();

  return {
    user,
    isLoading,
    error,
    isAuthenticated: !!user,
    login: login.mutate,
    logout: logout.mutate,
    register: register.mutate,
    loginAsync: login.mutateAsync,
    logoutAsync: logout.mutateAsync,
    registerAsync: register.mutateAsync,
  };
}
