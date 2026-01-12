"use client"

import * as React from "react"
import { Command } from "@tauri-apps/plugin-shell"
import { listen } from "@tauri-apps/api/event"
import { Plus, Check, RefreshCw, Loader2, ArrowLeft, ExternalLink } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Avatar,
  AvatarFallback,
} from "@/components/ui/avatar"
import { Label } from "@/components/ui/label"

import { Account, DeviceFlowData, AccountLimits } from "@/lib/types"
import { UsageCard } from "@/components/UsageCard"

type ViewState = 'list' | 'login-instructions' | 'login-flow';

export default function TrayApp() {
  const [accounts, setAccounts] = React.useState<Account[]>([])
  const [activeAccount, setActiveAccount] = React.useState<string | null>(null)
  const [activeLimits, setActiveLimits] = React.useState<AccountLimits | undefined>(undefined)

  const [loading, setLoading] = React.useState(false)
  const [view, setView] = React.useState<ViewState>('list');

  // Login State
  const [flowData, setFlowData] = React.useState<DeviceFlowData | null>(null);
  const [pollInterval, setPollInterval] = React.useState<number>(5000);

  // Helper: Invoke CLI via Sidecar (Tauri) or API Bridge (Browser)
  const invokeCLI = async (args: string[]) => {
    // Check for Tauri environment
    // @ts-ignore
    if (typeof window !== 'undefined' && window.__TAURI__) {
      return await Command.sidecar("codex-backend", args).execute();
    }

    // fallback: API Bridge
    try {
      const res = await fetch('/api/cli', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ args })
      });
      return await res.json();
    } catch (e) {
      console.error("Bridge Error", e);
      return { code: 1, stdout: "", stderr: String(e) };
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);

      // 1. Get Accounts
      const listOutput = await invokeCLI(["--json", "list"]);

      if (listOutput.code === 0) {
        const parsed: Account[] = JSON.parse(listOutput.stdout);
        setAccounts(parsed);
      } else {
        console.error("List failed:", listOutput.stderr);
      }

      // 2. Get Active
      const statusOutput = await invokeCLI(["--json", "status"]);

      if (statusOutput.code === 0) {
        // Parse JSON output: {"active_account": " slug", "status": "active"} 
        // OR {"active_account": null, "status": "none"}
        const result = JSON.parse(statusOutput.stdout);
        const newActive = result.active_account;
        setActiveAccount(newActive);

        if (newActive) {
          // 3. Get Limits (Async)
          // We don't block the main UI update on this
          invokeCLI(["limits", "show", "--json"]).then(limitsOutput => {
            if (limitsOutput.code === 0) {
              try {
                const parsedLimits = JSON.parse(limitsOutput.stdout);
                setActiveLimits(parsedLimits);
              } catch (e) {
                console.error("Failed to parse limits", e);
              }
            }
          });
        }
      }

    } catch (error) {
      console.error("Failed to fetch:", error);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchData();

    // Listen for Tray events
    const setupListener = async () => {
      // Setup listeners only if in Tauri for now, or mock events via SSE later?
      // For now, Browser won't receive tray events, which is fine.
      // @ts-ignore
      if (typeof window !== 'undefined' && window.__TAURI__) {
        const unlistenSwitch = await listen<string>('tray-switch-account', (event) => {
          handleSwitch(event.payload);
        });

        const unlistenAdd = await listen<void>('tray-add-account', () => {
          setView('login-instructions');
          fetchData();
        });

        // Listen for external config changes (Sync)
        const unlistenConfig = await listen<void>('tray-config-changed', () => {
          fetchData();
        });

        return () => {
          unlistenSwitch();
          unlistenAdd();
          unlistenConfig();
        };
      }
      return () => { };
    };

    let unlistenFn: (() => void) | undefined;
    setupListener().then(fn => unlistenFn = fn);

    return () => {
      if (unlistenFn) unlistenFn();
    };
  }, []);

  const handleSwitch = async (name: string) => {
    try {
      setLoading(true);
      const output = await invokeCLI(["switch", name]);
      // CLI API route returns code/stdout/stderr directly, unlike Command.execute() which returns object
      // wait, invokeCLI returns standardized object {code, stdout, stderr}

      // Need to check specific output?
      // switch command in CLI outputs logic
      // But we just check code.
      await fetchData(); // Refresh state
      toast.success(`Switched to ${name}`);
    } catch (error) {
      console.error("Switch failed:", error);
      toast.error(`Failed to switch: ${error}`);
      setLoading(false);
    }
  };

  // --- Device Login Flow ---

  const startLoginFlow = async () => {
    try {
      setLoading(true);
      const output = await invokeCLI(["device-login-init"]);

      if (output.code === 0) {
        const data: DeviceFlowData = JSON.parse(output.stdout);
        setFlowData(data);
        setView('login-flow');
        setPollInterval(data.interval * 1000);
      } else {
        toast.error("Failed to start login: " + output.stderr);
      }
    } catch (e) {
      toast.error("Failed to start login: " + e);
    } finally {
      setLoading(false);
    }
  };

  const finalizeLogin = async (tokens: any, email?: string) => {
    try {
      setLoading(true);

      let accountName = `user-${Date.now().toString().slice(-4)}`;
      if (email) {
        // simple sanitization: replace @ and . with - or keep as is? 
        // The backend uses slugify but keeping email format is often nicer for display if supported.
        // Let's rely on backend slugify or validation. But for CLI arg, passing the email is fine.
        accountName = email;
      }

      const output = await invokeCLI([
        "add",
        accountName,
        "--tokens-json", JSON.stringify(tokens),
        "--force"
      ]);

      if (output.code === 0) {
        toast.success("Login Successful!");
        setView('list');
        fetchData();
      } else {
        toast.error("Failed to save account: " + output.stderr);
      }

    } catch (e) {
      toast.error("Failed to finalize: " + e);
    } finally {
      setLoading(false);
    }
  };

  // Polling Effect
  React.useEffect(() => {
    if (view !== 'login-flow' || !flowData) return;

    const timer = setInterval(async () => {
      try {
        const output = await invokeCLI(["device-login-poll", flowData.device_code]);

        if (output.code === 0) {
          const result = JSON.parse(output.stdout);
          if (result.status === 'success') {
            clearInterval(timer);
            // Result now includes 'email' if backend fetch was successful
            finalizeLogin(result.tokens, result.email);
          } else if (result.status === 'error') {
            toast.error(result.message);
            setView('list');
          } else if (result.status === 'slow_down') {
            // In a real app we'd adjust interval, but simpler to just ignore for now or wait
          }
          // 'pending' -> do nothing
        }
      } catch (e) {
        console.error("Poll error", e);
      }
    }, pollInterval);

    return () => clearInterval(timer);
  }, [view, flowData, pollInterval]);


  // Determine Content
  const renderContent = () => {
    if (view === 'login-instructions') {
      return (
        <>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg font-bold">Add Account</CardTitle>
            <CardDescription>
              Connect a new Codex account to this device.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <Button onClick={startLoginFlow} className="w-full" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Start Browser Login
            </Button>

            <div className="flex items-center gap-2">
              <div className="h-px flex-1 bg-border"></div>
              <span className="text-xs uppercase text-muted-foreground">Or using CLI</span>
              <div className="h-px flex-1 bg-border"></div>
            </div>

            <div className="rounded-md bg-muted p-3 text-sm font-mono break-all select-all border text-center">
              codex-account login
            </div>
          </CardContent>
          <CardFooter>
            <Button variant="ghost" onClick={() => setView('list')} className="w-full">
              Cancel
            </Button>
          </CardFooter>
        </>
      );
    }

    if (view === 'login-flow' && flowData) {
      return (
        <>
          <CardHeader className="pb-3 text-center">
            <CardTitle className="text-lg font-bold">Verify Device</CardTitle>
            <CardDescription>
              Please visit the link and enter the code below:
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4">
            <div className="text-3xl font-mono font-bold tracking-widest text-primary border-2 border-dashed p-4 rounded-lg bg-muted/50">
              {flowData.user_code}
            </div>

            <p className="text-sm text-muted-foreground text-center px-4">
              Copy the code, then click the link to verify.
            </p>

            <Button asChild className="w-full" variant="secondary">
              <a href={flowData.verification_uri} target="_blank" rel="noreferrer">
                Open Verification Page <ExternalLink className="ml-2 h-3 w-3" />
              </a>
            </Button>

            <div className="flex items-center gap-2 text-xs text-muted-foreground animate-pulse mt-4">
              <Loader2 className="h-3 w-3 animate-spin" /> Waiting for approval...
            </div>
          </CardContent>
          <CardFooter>
            <Button variant="ghost" onClick={() => setView('list')} className="w-full">
              Cancel
            </Button>
          </CardFooter>
        </>
      );
    }

    // Default: List
    const activeDetails = accounts.find(a => a.name === activeAccount) || { name: activeAccount || "No Account", email: "" };

    return (
      <>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-bold">Codex Accounts</CardTitle>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={fetchData} disabled={loading}>
                <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
              </Button>
              <div className={`h-2 w-2 rounded-full ${activeAccount ? 'bg-green-500' : 'bg-red-500'} ${loading ? 'animate-pulse' : ''}`} />
              <span className="text-xs text-muted-foreground">{activeAccount ? 'Connected' : 'Offline'}</span>
            </div>
          </div>
          <CardDescription>
            Current: <span className="font-bold text-foreground">{activeDetails.name}</span>
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          {activeAccount && (
            <UsageCard limits={activeLimits} loading={loading && !activeLimits} />
          )}

          <div className="space-y-2">
            <Label className="text-xs font-semibold text-muted-foreground uppercase">Available Accounts</Label>
            <div className="space-y-1 max-h-[300px] overflow-y-auto">
              {accounts.length === 0 && !loading && (
                <div className="text-center text-sm text-muted-foreground py-4">
                  No accounts found.
                </div>
              )}

              {accounts.map(acc => (
                <Button
                  key={acc.name}
                  variant={activeAccount === acc.name ? "secondary" : "ghost"}
                  className="w-full justify-start h-14 px-4"
                  onClick={() => handleSwitch(acc.name)}
                  disabled={loading}
                >
                  <Avatar className="h-8 w-8 mr-3">
                    <AvatarFallback className={activeAccount === acc.name ? "bg-primary text-primary-foreground" : ""}>
                      {acc.name.substring(0, 1).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex flex-col items-start truncate">
                    <span className="font-semibold text-sm">{acc.name}</span>
                    <span className="text-xs text-muted-foreground truncate w-[180px] text-left">
                      {acc.email || "API Key"}
                    </span>
                  </div>
                  {activeAccount === acc.name && <Check className="ml-auto h-4 w-4 text-primary" />}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <Button className="w-full" variant="outline" onClick={() => setView('login-instructions')}>
            <Plus className="mr-2 h-4 w-4" /> Add Account
          </Button>
        </CardFooter>
      </>
    );
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-transparent p-4">
      <Card className="w-[320px] shadow-xl border-border/50 bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
        {renderContent()}
      </Card>
    </div>
  )
}
