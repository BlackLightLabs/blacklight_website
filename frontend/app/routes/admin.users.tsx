/**
 * Admin Users Page
 *
 * Allows administrators to view and manage all users in the system.
 * Features:
 * - User list with search and filtering
 * - Quick actions (activate/deactivate, change role)
 * - Click to view user details
 */

import { useState, useEffect } from "react";
import { Link } from "react-router";
import { adminApi, type UserListItem, type Role, type RoleWithPermissions } from "~/lib/admin-api";
import { Button } from "~/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "~/components/ui/table";
import { Input } from "~/components/ui/input";
import { Badge } from "~/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { toast } from "sonner";
import { Switch } from "~/components/ui/switch";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [roles, setRoles] = useState<RoleWithPermissions[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Load users and roles
  useEffect(() => {
    loadData();
  }, [searchQuery, roleFilter, statusFilter]);

  const loadData = async () => {
    try {
      setLoading(true);

      // Build filters
      const filters: any = {};
      if (searchQuery) filters.search = searchQuery;
      if (roleFilter !== "all") filters.role_id = parseInt(roleFilter);
      if (statusFilter !== "all") filters.is_active = statusFilter === "active";

      // Load users and roles in parallel
      const [usersData, rolesData] = await Promise.all([
        adminApi.users.listUsers(filters),
        adminApi.roles.listRoles(),
      ]);

      setUsers(usersData);
      setRoles(rolesData);
    } catch (error) {
      console.error("Error loading data:", error);
      toast.error("Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleUserStatus = async (userId: number, currentStatus: boolean) => {
    try {
      if (currentStatus) {
        await adminApi.users.deactivateUser(userId);
        toast.success("User deactivated");
      } else {
        await adminApi.users.activateUser(userId);
        toast.success("User activated");
      }
      loadData(); // Reload data
    } catch (error) {
      console.error("Error toggling user status:", error);
      toast.error("Failed to update user status");
    }
  };

  const handleChangeRole = async (userId: number, roleId: number) => {
    try {
      await adminApi.users.updateUserRole(userId, roleId);
      toast.success("User role updated");
      loadData(); // Reload data
    } catch (error) {
      console.error("Error updating role:", error);
      toast.error("Failed to update user role");
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <Card>
        <CardHeader>
          <CardTitle>User Management</CardTitle>
          <CardDescription>View and manage all users in the system</CardDescription>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="flex gap-4 mb-6">
            <div className="flex-1">
              <Input
                placeholder="Search by email or name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full"
              />
            </div>
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Roles</SelectItem>
                {roles.map((role) => (
                  <SelectItem key={role.id} value={role.id.toString()}>
                    {role.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Users</SelectItem>
                <SelectItem value="active">Active Only</SelectItem>
                <SelectItem value="inactive">Inactive Only</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Users Table */}
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Loading users...</div>
          ) : users.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No users found</div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Login</TableHead>
                    <TableHead>Joined</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-medium">
                        <Link to={`/admin/users/${user.id}`} className="hover:underline">
                          {user.email}
                        </Link>
                        {user.is_superuser && (
                          <Badge variant="destructive" className="ml-2">
                            Superuser
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>{user.full_name || "-"}</TableCell>
                      <TableCell>
                        <Select
                          value={user.role_id?.toString() || "none"}
                          onValueChange={(value) =>
                            value !== "none" && handleChangeRole(user.id, parseInt(value))
                          }
                        >
                          <SelectTrigger className="w-[140px]">
                            <SelectValue>{user.role_name || "No role"}</SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {roles.map((role) => (
                              <SelectItem key={role.id} value={role.id.toString()}>
                                {role.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={user.is_active}
                            onCheckedChange={() => handleToggleUserStatus(user.id, user.is_active)}
                          />
                          <span className="text-sm">
                            {user.is_active ? (
                              <Badge variant="default">Active</Badge>
                            ) : (
                              <Badge variant="secondary">Inactive</Badge>
                            )}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(user.last_login_at)}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(user.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Link to={`/admin/users/${user.id}`}>
                          <Button variant="outline" size="sm">
                            View Details
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Summary */}
          <div className="mt-4 text-sm text-muted-foreground">
            Showing {users.length} user{users.length !== 1 ? "s" : ""}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
