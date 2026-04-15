/**
 * Admin User Detail Page
 *
 * Displays detailed information about a specific user and allows editing.
 * Features:
 * - User information display
 * - Role assignment
 * - Account status management
 * - Permission overview (inherited from role)
 */

import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router";
import { adminApi, type UserWithRole, type RoleWithPermissions } from "~/lib/admin-api";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Badge } from "~/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import { toast } from "sonner";
import { Separator } from "~/components/ui/separator";
import { Switch } from "~/components/ui/switch";
import { ArrowLeft, Mail, Shield, User, Calendar, CheckCircle2, XCircle } from "lucide-react";

export default function AdminUserDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [user, setUser] = useState<UserWithRole | null>(null);
  const [roles, setRoles] = useState<RoleWithPermissions[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      loadUser();
      loadRoles();
    }
  }, [id]);

  const loadUser = async () => {
    try {
      setLoading(true);
      const userData = await adminApi.users.getUserDetails(parseInt(id!));
      setUser(userData);
    } catch (error) {
      console.error("Error loading user:", error);
      toast.error("Failed to load user details");
    } finally {
      setLoading(false);
    }
  };

  const loadRoles = async () => {
    try {
      const rolesData = await adminApi.roles.listRoles();
      setRoles(rolesData);
    } catch (error) {
      console.error("Error loading roles:", error);
    }
  };

  const handleToggleStatus = async () => {
    if (!user) return;

    try {
      if (user.is_active) {
        await adminApi.users.deactivateUser(user.id);
        toast.success("User deactivated");
      } else {
        await adminApi.users.activateUser(user.id);
        toast.success("User activated");
      }
      loadUser(); // Reload user data
    } catch (error) {
      console.error("Error toggling status:", error);
      toast.error("Failed to update user status");
    }
  };

  const handleRoleChange = async (roleId: string) => {
    if (!user) return;

    try {
      await adminApi.users.updateUserRole(user.id, parseInt(roleId));
      toast.success("User role updated");
      loadUser(); // Reload user data
    } catch (error) {
      console.error("Error updating role:", error);
      toast.error("Failed to update user role");
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="text-center py-8 text-muted-foreground">Loading user details...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container mx-auto py-8 px-4">
        <Card>
          <CardContent className="py-8">
            <div className="text-center text-muted-foreground">User not found</div>
            <div className="text-center mt-4">
              <Button onClick={() => navigate("/admin/users")}>Back to Users</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const currentRole = roles.find((r) => r.id === user.role_id);

  return (
    <div className="container mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link to="/admin/users">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Users
          </Button>
        </Link>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* User Information Card */}
        <Card>
          <CardHeader>
            <CardTitle>User Information</CardTitle>
            <CardDescription>Basic account details and status</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <div>
                <div className="text-sm font-medium">Email</div>
                <div className="text-sm text-muted-foreground">{user.email}</div>
              </div>
            </div>

            <Separator />

            <div className="flex items-center gap-3">
              <User className="h-4 w-4 text-muted-foreground" />
              <div>
                <div className="text-sm font-medium">Full Name</div>
                <div className="text-sm text-muted-foreground">{user.full_name || "Not set"}</div>
              </div>
            </div>

            <Separator />

            <div className="flex items-center gap-3">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <div className="text-sm font-medium">Joined</div>
                <div className="text-sm text-muted-foreground">{formatDate(user.created_at)}</div>
              </div>
            </div>

            <Separator />

            <div className="flex items-center gap-3">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <div className="text-sm font-medium">Last Login</div>
                <div className="text-sm text-muted-foreground">
                  {formatDate(user.last_login_at)}
                </div>
              </div>
            </div>

            <Separator />

            <div className="space-y-2">
              <div className="text-sm font-medium">Account Flags</div>
              <div className="flex flex-wrap gap-2">
                {user.is_superuser && <Badge variant="destructive">Superuser</Badge>}
                {user.is_verified ? (
                  <Badge variant="default">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Verified
                  </Badge>
                ) : (
                  <Badge variant="secondary">
                    <XCircle className="h-3 w-3 mr-1" />
                    Not Verified
                  </Badge>
                )}
                {user.is_active ? (
                  <Badge variant="default">Active</Badge>
                ) : (
                  <Badge variant="secondary">Inactive</Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Role Management Card */}
        <Card>
          <CardHeader>
            <CardTitle>Role & Permissions</CardTitle>
            <CardDescription>Manage user role and view permissions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Assigned Role</label>
              <Select
                value={user.role_id?.toString() || "none"}
                onValueChange={handleRoleChange}
                disabled={user.is_superuser}
              >
                <SelectTrigger>
                  <SelectValue>
                    {user.is_superuser
                      ? "Superuser (All Permissions)"
                      : currentRole?.name || "No role assigned"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {roles.map((role) => (
                    <SelectItem key={role.id} value={role.id.toString()}>
                      {role.name}
                      {role.description && (
                        <span className="text-xs text-muted-foreground ml-2">
                          {role.description}
                        </span>
                      )}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {user.is_superuser && (
                <p className="text-xs text-muted-foreground mt-2">
                  Superusers have all permissions and cannot be assigned a role.
                </p>
              )}
            </div>

            <Separator />

            {currentRole && (
              <div>
                <div className="text-sm font-medium mb-3">Permissions ({currentRole.permissions.length})</div>
                {currentRole.permissions.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No permissions assigned to this role</p>
                ) : (
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {currentRole.permissions.map((permission) => (
                      <div
                        key={permission.id}
                        className="flex items-start gap-2 p-2 rounded-md bg-muted/50"
                      >
                        <Shield className="h-4 w-4 mt-0.5 text-primary" />
                        <div className="flex-1">
                          <div className="text-sm font-medium">{permission.name}</div>
                          {permission.description && (
                            <div className="text-xs text-muted-foreground">
                              {permission.description}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {user.is_superuser && (
              <div className="p-3 rounded-md bg-primary/10 border border-primary/20">
                <div className="flex items-start gap-2">
                  <Shield className="h-4 w-4 mt-0.5 text-primary" />
                  <div className="text-sm">
                    <div className="font-medium">All Permissions</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      This user has superuser privileges and can perform any action.
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Account Management Card */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Account Management</CardTitle>
            <CardDescription>Manage account status and settings</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Account Status</div>
                <div className="text-sm text-muted-foreground">
                  {user.is_active
                    ? "This account is active and can log in"
                    : "This account is deactivated and cannot log in"}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium">
                  {user.is_active ? "Active" : "Inactive"}
                </span>
                <Switch checked={user.is_active} onCheckedChange={handleToggleStatus} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
