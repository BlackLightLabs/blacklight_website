import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import { Alert, AlertDescription } from "./ui/alert";

export type BuildStage = "code_generation" | "syntax_check" | "testing" | "ready" | "failed";

export interface BuildStatusPanelProps {
  stage: BuildStage | null;
  progress: number;
  error?: string;
  className?: string;
}

const stageLabels: Record<BuildStage, string> = {
  code_generation: "Generating Code",
  syntax_check: "Validating Syntax",
  testing: "Running Tests",
  ready: "Agent Ready",
  failed: "Build Failed",
};

const stageProgress: Record<BuildStage, number> = {
  code_generation: 25,
  syntax_check: 50,
  testing: 75,
  ready: 100,
  failed: 0,
};

/**
 * BuildStatusPanel - Shows agent build progress
 *
 * Displays current build stage, progress bar, and any errors.
 */
export function BuildStatusPanel({ stage, progress, error, className = "" }: BuildStatusPanelProps) {
  if (!stage) {
    return null;
  }

  const displayProgress = progress || stageProgress[stage];
  const isComplete = stage === "ready";
  const isFailed = stage === "failed";

  return (
    <div className={`border-t bg-muted/30 p-4 ${className}`}>
      <div className="mx-auto max-w-4xl">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Build Status:</span>
            <Badge variant={isComplete ? "default" : isFailed ? "destructive" : "secondary"}>
              {stageLabels[stage]}
            </Badge>
          </div>
          <span className="text-sm text-muted-foreground">{displayProgress}%</span>
        </div>

        <Progress value={displayProgress} className="h-2" />

        {error && (
          <Alert variant="destructive" className="mt-3">
            <AlertDescription>
              <div className="text-sm">{error}</div>
            </AlertDescription>
          </Alert>
        )}

        {isComplete && (
          <Alert className="mt-3 border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20">
            <AlertDescription>
              <div className="text-sm text-green-800 dark:text-green-200">
                ✓ Your agent has been built successfully and is ready to use!
              </div>
            </AlertDescription>
          </Alert>
        )}
      </div>
    </div>
  );
}
