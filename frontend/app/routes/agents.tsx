import { useState, useEffect } from "react";
import { Link } from "react-router";
import type { Route } from "./+types/agents";
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
import { Skeleton } from "../components/ui/skeleton";
import { Separator } from "../components/ui/separator";
import { Alert, AlertDescription } from "../components/ui/alert";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { api, type AgentDetails } from "../lib/api";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "My Agents - Agent Builder" },
    { name: "description", content: "View and manage your AI agents" },
  ];
}

export default function Agents() {
  const [agents, setAgents] = useState<AgentDetails[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      setIsLoading(true);
      const data = await api.listAgents();
      setAgents(data);
      setError(null);
    } catch (err) {
      setError("Failed to load agents. Please try again.");
      console.error("Error loading agents:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="flex-1">
        <div className="mx-auto max-w-6xl">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h1 className="mb-2 text-3xl font-bold">My Agents</h1>
              <p className="text-muted-foreground">View and manage your AI agents</p>
            </div>
            <Link to="/create-agent">
              <Button>Create New Agent</Button>
            </Link>
          </div>

          {isLoading ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <Card key={i}>
                  <CardHeader>
                    <Skeleton className="mb-2 h-6 w-3/4" />
                    <Skeleton className="h-4 w-1/4" />
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-2/3" />
                  </CardContent>
                  <CardFooter>
                    <Skeleton className="h-10 w-full" />
                  </CardFooter>
                </Card>
              ))}
            </div>
          ) : error ? (
            <Alert variant="destructive">
              <AlertDescription>
                <p className="mb-2 font-semibold">{error}</p>
                <Button onClick={loadAgents} variant="outline" size="sm">
                  Try Again
                </Button>
              </AlertDescription>
            </Alert>
          ) : agents.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>No Agents Yet</CardTitle>
                <CardDescription>Get started by creating your first AI agent</CardDescription>
              </CardHeader>
              <CardFooter>
                <Link to="/create-agent">
                  <Button>Create Your First Agent</Button>
                </Link>
              </CardFooter>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {agents.map((agent) => (
                <Card key={agent.agent_id} className="transition-shadow hover:shadow-lg">
                  <CardHeader>
                    <div className="mb-2 flex items-start justify-between">
                      <Badge
                        variant={agent.status === "ready" ? "default" : "secondary"}
                        className={agent.status === "ready" ? "bg-green-600" : ""}
                      >
                        {agent.status === "ready" ? "● Ready" : "○ " + agent.status}
                      </Badge>
                      {agent.total_executions > 0 && (
                        <Badge variant="outline">{agent.total_executions} runs</Badge>
                      )}
                    </div>
                    <CardTitle className="line-clamp-2 text-lg">{agent.description}</CardTitle>
                    <CardDescription className="text-xs">
                      Created {new Date(agent.created_at).toLocaleDateString()}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3 text-sm">
                      <Separator />
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Total Cost</span>
                        <span className="text-lg font-bold">${agent.total_cost.toFixed(2)}</span>
                      </div>
                      {agent.estimated_cost_per_run && (
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Per run</span>
                          <Badge variant="secondary">
                            ${agent.estimated_cost_per_run.toFixed(2)}
                          </Badge>
                        </div>
                      )}
                    </div>
                  </CardContent>
                  <CardFooter>
                    <Link to={`/agents/${agent.agent_id}`} className="w-full">
                      <Button variant="outline" className="w-full">
                        View & Execute →
                      </Button>
                    </Link>
                  </CardFooter>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}
