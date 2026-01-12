import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AccountLimits } from "@/lib/types"
import { HelpCircle } from "lucide-react"
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip"

interface UsageCardProps {
    limits?: AccountLimits;
    loading?: boolean;
}

export function UsageCard({ limits, loading }: UsageCardProps) {
    if (loading) {
        return (
            <Card className="w-full animate-pulse border-border/50">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">Usage Quotas</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="h-4 bg-muted rounded w-3/4"></div>
                    <div className="h-4 bg-muted rounded w-1/2"></div>
                </CardContent>
            </Card>
        )
    }

    if (!limits) {
        return null; // Or show empty state/placeholder only if requested
    }

    // Helpers
    const renderBar = (label: string, data?: { used: number, limit: number, reset_in_minutes?: number, reset_in_days?: number }) => {
        if (!data) return null;

        const pct = Math.min((data.used / data.limit) * 100, 100);
        let colorClass = "bg-green-500";
        if (pct >= 80) colorClass = "bg-yellow-500";
        if (pct >= 95) colorClass = "bg-red-500 animate-pulse";

        const resetText = data.reset_in_minutes
            ? `Resets in ${Math.floor(data.reset_in_minutes / 60)}h ${data.reset_in_minutes % 60}m`
            : `Resets in ${data.reset_in_days} days`;

        return (
            <div className="space-y-1">
                <div className="flex justify-between text-xs items-end">
                    <span className="font-medium text-muted-foreground">{label}</span>
                    <div className="text-right">
                        <span className="text-foreground block">{data.used} / {data.limit} ({pct.toFixed(0)}%)</span>
                    </div>
                </div>
                <div className="relative pt-1">
                    <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                        <div className={`h-full ${colorClass} transition-all duration-500`} style={{ width: `${pct}%` }} />
                    </div>
                </div>
                <div className="flex justify-end">
                    <span className="text-[10px] text-muted-foreground">{resetText}</span>
                </div>
            </div>
        )
    };

    return (
        <Card className="w-full border-border/50 bg-card/50">
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium text-muted-foreground">Usage Quotas</CardTitle>
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger>
                                <HelpCircle className="h-3 w-3 text-muted-foreground/50" />
                            </TooltipTrigger>
                            <TooltipContent>
                                <p>API usage limits for your account.</p>
                                <p>Updated automatically.</p>
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {renderBar("5-Hour Limit", limits.limit_5h)}
                {renderBar("Weekly Limit", limits.limit_weekly)}
            </CardContent>
        </Card>
    )
}
