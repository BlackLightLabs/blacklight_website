import { Link } from "react-router";
import type { Route } from "./+types/home";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { Avatar, AvatarFallback } from "../components/ui/avatar";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Agent Builder - Build AI Agents Through Conversation" },
    {
      name: "description",
      content: "Create custom AI agents using LangGraph through a simple conversational interface",
    },
  ];
}

export default function Home() {
  return (
    <div className="flex-1">
      <div className="mx-auto max-w-6xl py-12 md:py-20">
        <div className="mb-12 text-center">
          <div className="mb-4 flex justify-center">
            <Badge variant="secondary" className="mb-4">
              ✨ Powered by LangGraph & OpenAI
            </Badge>
          </div>
          <h1 className="mb-4 text-4xl font-bold md:text-6xl">
            Build AI Agents Through Conversation
          </h1>
          <p className="text-muted-foreground mx-auto mb-8 max-w-2xl text-xl">
            Describe what you want your agent to do, and we'll build it for you using LangGraph. No
            coding required.
          </p>
          <div className="mb-8 flex justify-center gap-4">
            <Link to="/create-agent">
              <Button size="lg">Create Your First Agent</Button>
            </Link>
            <Link to="/agents">
              <Button size="lg" variant="outline">
                View My Agents
              </Button>
            </Link>
          </div>
          <div className="text-muted-foreground flex items-center justify-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Avatar className="h-8 w-8">
                <AvatarFallback>AI</AvatarFallback>
              </Avatar>
              <span>500+ Agents Created</span>
            </div>
            <Separator orientation="vertical" className="h-4" />
            <span>⚡ Fast Setup</span>
            <Separator orientation="vertical" className="h-4" />
            <span>💰 Pay Per Use</span>
          </div>
        </div>

        <Separator className="my-12" />

        <div className="mt-16 grid gap-6 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>💬 Conversational Design</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Simply tell us what you want your agent to do. We'll ask questions to understand
                your needs and build the perfect agent for you.
              </CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>⚡ Powered by LangGraph</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Your agents are built using LangGraph, a powerful framework for creating stateful,
                multi-step AI workflows.
              </CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>💰 Pay Per Use</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Only pay when you execute your agents. No upfront costs, no subscriptions. Clear
                pricing per execution.
              </CardDescription>
            </CardContent>
          </Card>
        </div>

        <div className="mt-16 text-center">
          <h2 className="mb-4 text-2xl font-bold">Example Agent Ideas</h2>
          <div className="mx-auto grid max-w-3xl gap-4 text-left md:grid-cols-2">
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm">
                  "Check my email daily for potential sales prospects and continue down the sales
                  pipeline"
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm">
                  "Monitor my competitor's websites and notify me when they launch new features"
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm">
                  "Analyze customer feedback from multiple sources and generate weekly reports"
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm">
                  "Automate my social media posting based on trending topics in my industry"
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
