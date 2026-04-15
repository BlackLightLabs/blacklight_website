/**
 * Admin Roles Page
 *
 * Allows administrators to manage roles and their permissions.
 * Features:
 * - View all roles
 * - Create new roles
 * - Edit existing roles
 * - Assign/remove permissions from roles
 * - Delete roles (with safety checks)
 */

import { useState, useEffect } from "react";
import { adminApi, type RoleWithPermissions, type Permission } from "~/lib/admin-api";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Badge } from "~/components/ui/badge";
import { Input } from "~/components/ui/input";
import { Textarea } from "~/components/ui/textarea";
import { Checkbox } from "~/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "~/components/ui/dialog";
import { toast } from "sonner";
import { Separator } from "~/components/ui/separator";
import { Shield, Plus, Edit, Trash2 } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";

export default function AdminRolesPage() {
  const [roles, setRoles] = useState<RoleWithPermissions[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<RoleWithPermissions | null>(null);

  // Form state
  const [roleName, setRoleName] = useState("");
  const [roleDescription, setRoleDescription] = useState("");
  const [selectedPermissions, setSelectedPermissions] = useState<number[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [rolesData, permissionsData] = await Promise.all([
        adminApi.roles.listRoles(),
        adminApi.permissions.listPermissions(),
      ]);
      setRoles(rolesData);
      setPermissions(permissionsData);
    } catch (error) {
      console.error("Error loading data:", error);
      toast.error("Failed to load roles");
    } finally {
      setLoading(false);
    }
  };

  const openCreateDialog = () => {
    setRoleName("");
    setRoleDescription("");
    setSelectedPermissions([]);
    setCreateDialogOpen(true);
  };

  const openEditDialog = (role: RoleWithPermissions) => {
    setSelectedRole(role);
    setRoleName(role.name);
    setRoleDescription(role.description || "");
    setSelectedPermissions(role.permissions.map((p) => p.id));
    setEditDialogOpen(true);
  };

  const handleCreateRole = async () => {
    try {
      await adminApi.roles.createRole({
        name: roleName,
        description: roleDescription || undefined,
        permission_ids: selectedPermissions,
      });
      toast.success("Role created successfully");
      setCreateDialogOpen(false);
      loadData();
    } catch (error) {
      console.error("Error creating role:", error);
      toast.error("Failed to create role");
    }
  };

  const handleUpdateRole = async () => {
    if (!selectedRole) return;

    try {
      await adminApi.roles.updateRole(selectedRole.id, {
        name: roleName,
        description: roleDescription || undefined,
        permission_ids: selectedPermissions,
      });
      toast.success("Role updated successfully");
      setEditDialogOpen(false);
      loadData();
    } catch (error) {
      console.error("Error updating role:", error);
      toast.error("Failed to update role");
    }
  };

  const handleDeleteRole = async (roleId: number, roleName: string) => {
    if (!confirm(`Are you sure you want to delete the role "${roleName}"? This cannot be undone.`)) {
      return;
    }

    try {
      await adminApi.roles.deleteRole(roleId);
      toast.success("Role deleted successfully");
      loadData();
    } catch (error: any) {
      console.error("Error deleting role:", error);
      toast.error(error.message || "Failed to delete role");
    }
  };

  const togglePermission = (permissionId: number) => {
    setSelectedPermissions((prev) =>
      prev.includes(permissionId)
        ? prev.filter((id) => id !== permissionId)
        : [...prev, permissionId],
    );
  };

  // Group permissions by resource
  const permissionsByResource = permissions.reduce(
    (acc, permission) => {
      if (!acc[permission.resource]) {
        acc[permission.resource] = [];
      }
      acc[permission.resource].push(permission);
      return acc;
    },
    {} as Record<string, Permission[]>,
  );

  const PermissionSelector = () => (
    <Tabs defaultValue={Object.keys(permissionsByResource)[0]} className="w-full">
      <TabsList className="w-full">
        {Object.keys(permissionsByResource).map((resource) => (
          <TabsTrigger key={resource} value={resource} className="flex-1">
            {resource}
          </TabsTrigger>
        ))}
      </TabsList>
      {Object.entries(permissionsByResource).map(([resource, perms]) => (
        <TabsContent key={resource} value={resource} className="mt-4">
          <div className="space-y-2">
            {perms.map((permission) => (
              <div key={permission.id} className="flex items-start gap-3 p-2 rounded-md hover:bg-muted/50">
                <Checkbox
                  id={`perm-${permission.id}`}
                  checked={selectedPermissions.includes(permission.id)}
                  onCheckedChange={() => togglePermission(permission.id)}
                />
                <label
                  htmlFor={`perm-${permission.id}`}
                  className="flex-1 cursor-pointer text-sm"
                >
                  <div className="font-medium">{permission.name}</div>
                  {permission.description && (
                    <div className="text-xs text-muted-foreground">{permission.description}</div>
                  )}
                </label>
              </div>
            ))}
          </div>
        </TabsContent>
      ))}
    </Tabs>
  );

  if (loading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="text-center py-8 text-muted-foreground">Loading roles...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Role Management</CardTitle>
              <CardDescription>Manage roles and their permissions</CardDescription>
            </div>
            <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button onClick={openCreateDialog}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Role
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>Create New Role</DialogTitle>
                  <DialogDescription>
                    Create a new role and assign permissions to it
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">Role Name</label>
                    <Input
                      placeholder="e.g., moderator"
                      value={roleName}
                      onChange={(e) => setRoleName(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-2 block">Description</label>
                    <Textarea
                      placeholder="Brief description of this role..."
                      value={roleDescription}
                      onChange={(e) => setRoleDescription(e.target.value)}
                      rows={3}
                    />
                  </div>
                  <Separator />
                  <div>
                    <label className="text-sm font-medium mb-3 block">
                      Permissions ({selectedPermissions.length} selected)
                    </label>
                    <PermissionSelector />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateRole} disabled={!roleName.trim()}>
                    Create Role
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {roles.map((role) => (
              <Card key={role.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-lg">{role.name}</CardTitle>
                        <Badge variant="secondary">{role.permissions.length} permissions</Badge>
                      </div>
                      {role.description && (
                        <CardDescription className="mt-1">{role.description}</CardDescription>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => openEditDialog(role)}>
                        <Edit className="h-4 w-4 mr-1" />
                        Edit
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteRole(role.id, role.name)}
                      >
                        <Trash2 className="h-4 w-4 mr-1" />
                        Delete
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-sm font-medium mb-3">Permissions:</div>
                  {role.permissions.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No permissions assigned</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {role.permissions.map((permission) => (
                        <Badge key={permission.id} variant="outline">
                          <Shield className="h-3 w-3 mr-1" />
                          {permission.name}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Role</DialogTitle>
            <DialogDescription>Update role details and permissions</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Role Name</label>
              <Input
                placeholder="e.g., moderator"
                value={roleName}
                onChange={(e) => setRoleName(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Description</label>
              <Textarea
                placeholder="Brief description of this role..."
                value={roleDescription}
                onChange={(e) => setRoleDescription(e.target.value)}
                rows={3}
              />
            </div>
            <Separator />
            <div>
              <label className="text-sm font-medium mb-3 block">
                Permissions ({selectedPermissions.length} selected)
              </label>
              <PermissionSelector />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateRole} disabled={!roleName.trim()}>
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
