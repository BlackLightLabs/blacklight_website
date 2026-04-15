import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("login", "routes/login.tsx"),
  route("signup", "routes/signup.tsx"),
  route("create-agent", "routes/create-agent.tsx"),
  route("agents", "routes/agents.tsx"),
  route("agents/:id", "routes/agents.$id.tsx"),
  route("settings", "routes/settings.tsx"),

  // OAuth success route (redirect_url after OAuth callback completes)
  route("oauth-success", "routes/oauth-success.tsx"),

  // Admin routes
  route("admin/users", "routes/admin.users.tsx"),
  route("admin/users/:id", "routes/admin.users.$id.tsx"),
  route("admin/roles", "routes/admin.roles.tsx"),
] satisfies RouteConfig;
