import { useState, useEffect } from "react";
import { useParams, Link } from "react-router";
import type { Route } from "./+types/agents.$id";
import { Button } from "../components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../components/ui/dialog";
import { Progress } from "../components/ui/progress";
import { Skeleton } from "../components/ui/skeleton";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "../components/ui/breadcrumb";
import { Alert, AlertDescription } from "../components/ui/alert";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { toast } from "sonner";
import { api, type AgentDetails, type AgentExecuteResponse } from "../lib/api";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Agent Details - Agent Builder" },
    { name: "description", content: "View and execute your AI agent" },
  ];
}

function AgentDetailPage() {
  const { id } = useParams();
  const [agent, setAgent] = useState<AgentDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<AgentExecuteResponse | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [executionProgress, setExecutionProgress] = useState(0);

  useEffect(() => {
    if (id) {
      loadAgent(id);
    }
  }, [id]);

  const loadAgent = async (agentId: string) => {
    try {
      setIsLoading(true);
      const data = await api.getAgent(agentId);
      setAgent(data);
      setError(null);
    } catch (err) {
      setError("Failed to load agent. Please try again.");
      console.error("Error loading agent:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!id) return;

    try {
      setIsExecuting(true);
      setIsDialogOpen(false);
      setExecutionProgress(0);

      toast.info("Executing agent...", {
        description: "Your agent is now running.",
      });

      // Simulate progress
      const progressInterval = setInterval(() => {
        setExecutionProgress((prev) => {
          if (prev >= 90) return prev;
          return prev + 10;
        });
      }, 200);

      const result = await api.executeAgent({ agent_id: id });

      clearInterval(progressInterval);
      setExecutionProgress(100);
      setExecutionResult(result);

      toast.success("Agent executed successfully!", {
        description: `Cost: $${result.cost?.toFixed(2) || "0.00"}`,
      });

      // Reload agent data to update metrics
      if (id) {
        await loadAgent(id);
      }
    } catch (err) {
      setError("Failed to execute agent. Please try again.");
      toast.error("Execution failed", {
        description: "There was an error executing your agent.",
      });
      console.error("Error executing agent:", err);
    } finally {
      setIsExecuting(false);
      setExecutionProgress(0);
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1">
        <div className="mx-auto max-w-4xl space-y-6">
          <Skeleton className="h-8 w-64" />
          <Card>
            <CardHeader>
              <Skeleton className="mb-2 h-6 w-48" />
              <Skeleton className="h-4 w-32" />
            </CardHeader>
            <CardContent className="space-y-4">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (error && !agent) {
    return (
      <div className="flex-1">
        <div className="mx-auto max-w-4xl">
          <Card>
            <CardContent className="pt-6">
              <p className="text-destructive">{error}</p>
              <Link to="/agents">
                <Button className="mt-4">Back to Agents</Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="flex-1">
        <div className="mx-auto max-w-4xl">
          <Card>
            <CardContent className="pt-6">
              <p>Agent not found</p>
              <Link to="/agents">
                <Button className="mt-4">Back to Agents</Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1">
      <div className="mx-auto max-w-4xl">
        <Breadcrumb className="mb-6">
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link to="/">Home</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link to="/agents">Agents</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>Agent Details</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>

        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="mb-2 text-3xl font-bold">Agent Details</h1>
            <p className="text-muted-foreground">View and execute your agent</p>
          </div>
          <Badge
            variant={agent.status === "ready" ? "default" : "secondary"}
            className={agent.status === "ready" ? "bg-green-600" : ""}
          >
            {agent.status === "ready" ? "● Ready" : "○ " + agent.status}
          </Badge>
        </div>

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="execute">Execute</TabsTrigger>
            <TabsTrigger value="technical">Technical</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Agent Information</CardTitle>
                <CardDescription>Details about your agent</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h3 className="text-muted-foreground mb-2 text-sm font-semibold">Description</h3>
                  <p className="text-sm">{agent.description}</p>
                </div>
                <Separator />
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="text-muted-foreground mb-2 text-sm font-semibold">Agent ID</h3>
                    <p className="font-mono text-xs">{agent.agent_id}</p>
                  </div>
                  <div>
                    <h3 className="text-muted-foreground mb-2 text-sm font-semibold">Created</h3>
                    <p className="text-sm">{new Date(agent.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Usage & Billing</CardTitle>
                <CardDescription>Track your agent's usage and costs</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Card>
                    <CardHeader className="pb-3">
                      <CardDescription>Total Executions</CardDescription>
                      <CardTitle className="text-3xl">{agent.total_executions}</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card>
                    <CardHeader className="pb-3">
                      <CardDescription>Total Cost</CardDescription>
                      <CardTitle className="text-3xl">${agent.total_cost.toFixed(2)}</CardTitle>
                    </CardHeader>
                  </Card>
                </div>
                {agent.estimated_cost_per_run && (
                  <>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground text-sm">Estimated Cost per Run</span>
                      <Badge variant="secondary" className="text-base">
                        ${agent.estimated_cost_per_run.toFixed(2)}
                      </Badge>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="execute" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Execute Agent</CardTitle>
                <CardDescription>Run your agent and view results</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {isExecuting && executionProgress > 0 && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Execution Progress</span>
                      <span className="font-semibold">{executionProgress}%</span>
                    </div>
                    <Progress value={executionProgress} />
                  </div>
                )}

                {executionResult && (
                  <Alert className="border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20">
                    <AlertDescription>
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <Badge className="bg-green-600">Success</Badge>
                          <span className="text-sm font-semibold">Agent executed successfully</span>
                        </div>
                        <Separator />
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">Status</span>
                            <p className="font-semibold">{executionResult.status}</p>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Cost</span>
                            <p className="font-semibold">
                              ${executionResult.cost?.toFixed(2) || "0.00"}
                            </p>
                          </div>
                        </div>
                        <div>
                          <span className="text-muted-foreground text-xs">Execution ID</span>
                          <p className="font-mono text-xs">{executionResult.execution_id}</p>
                        </div>
                        {executionResult.result && (
                          <>
                            <Separator />
                            <div>
                              <span className="mb-2 block text-sm font-semibold">Result</span>
                              <pre className="bg-background max-h-64 overflow-auto rounded p-3 text-xs">
                                {JSON.stringify(executionResult.result, null, 2)}
                              </pre>
                            </div>
                          </>
                        )}
                      </div>
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
              <CardFooter>
                <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                  <DialogTrigger asChild>
                    <Button disabled={isExecuting || agent.status !== "ready"} className="w-full">
                      {isExecuting ? "Executing..." : "Execute Agent"}
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Confirm Execution</DialogTitle>
                      <DialogDescription>
                        You are about to execute this agent. This action will incur a charge.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3 py-4">
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground text-sm">Estimated Cost</span>
                        <Badge variant="secondary" className="text-base">
                          ${agent.estimated_cost_per_run?.toFixed(2) || "0.10"}
                        </Badge>
                      </div>
                      <Separator />
                      <p className="text-muted-foreground text-sm">
                        The actual cost may vary based on agent execution time and resources used.
                      </p>
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                        Cancel
                      </Button>
                      <Button onClick={handleExecute}>Confirm & Execute</Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </CardFooter>
            </Card>
          </TabsContent>

          <TabsContent value="technical" className="space-y-6">
            {agent.graph_structure && (
              <Card>
                <CardHeader>
                  <CardTitle>Agent Structure</CardTitle>
                  <CardDescription>
                    Technical details about your agent's LangGraph workflow
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <pre className="bg-muted max-h-96 overflow-auto rounded p-4 text-xs">
                    {JSON.stringify(agent.graph_structure, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default function AgentDetail() {
  return (
    <ProtectedRoute>
      <AgentDetailPage />
    </ProtectedRoute>
  );
}
