"use client";

import { useEffect, useState } from "react";
import { Command } from "@tauri-apps/plugin-shell";
import { Check, ChevronsUpDown, Plus, User } from "lucide-react";
import { cn } from "@/lib/utils";

import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuGroup,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface Account {
    name: string;
    email?: string;
    type?: string;
    tags?: string[];
}

export function AccountSwitcher() {
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [activeAccount, setActiveAccount] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        try {
            setLoading(true);
            // 1. Get Accounts (JSON)
            // Note: This requires the binary to be authorized in macOS Keychain
            const listCmd = Command.create("codex-backend", ["--json", "list"]);
            const listOutput = await listCmd.execute();

            if (listOutput.code === 0) {
                const parsed: Account[] = JSON.parse(listOutput.stdout);
                setAccounts(parsed);
            } else {
                console.error("List failed:", listOutput.stderr);
            }

            // 2. Get Active Status
            const statusCmd = Command.create("codex-backend", ["status"]);
            const statusOutput = await statusCmd.execute();

            if (statusOutput.code === 0) {
                // Output might be "  current-account  "
                setActiveAccount(statusOutput.stdout.trim());
            }

        } catch (error) {
            console.error("Failed to fetch accounts:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSwitch = async (name: string) => {
        try {
            const cmd = Command.create("codex-backend", ["switch", name]);
            await cmd.execute();
            // Refresh
            fetchData();
        } catch (error) {
            console.error("Switch failed:", error);
        }
    };

    useEffect(() => {
        fetchData();
        // Poll every 5s? Or just once.
    }, []);

    const activeData = accounts.find((a) => a.name === activeAccount) || { name: activeAccount || "Select Account", email: "" };

    return (
        <div className="p-4">
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button
                        variant="outline"
                        role="combobox"
                        aria-label="Select account"
                        className="w-[250px] justify-between"
                    >
                        <div className="flex items-center gap-2 overflow-hidden">
                            <Avatar className="h-6 w-6">
                                <AvatarImage src="" />
                                <AvatarFallback><User className="h-4 w-4" /></AvatarFallback>
                            </Avatar>
                            <div className="flex flex-col items-start truncate text-xs">
                                <span className="font-medium">{activeData.name}</span>
                                {activeData.email && <span className="text-muted-foreground">{activeData.email}</span>}
                            </div>
                        </div>
                        <ChevronsUpDown className="ml-auto h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-[250px]">
                    <DropdownMenuLabel>Codex Accounts</DropdownMenuLabel>
                    <DropdownMenuGroup>
                        {accounts.map((account) => (
                            <DropdownMenuItem
                                key={account.name}
                                onSelect={() => handleSwitch(account.name)}
                                className="gap-2"
                            >
                                <div className="flex flex-col">
                                    <span className="font-medium">{account.name}</span>
                                    <span className="text-xs text-muted-foreground">{account.email}</span>
                                </div>
                                {account.name === activeAccount && (
                                    <Check className="ml-auto h-4 w-4" />
                                )}
                            </DropdownMenuItem>
                        ))}
                    </DropdownMenuGroup>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem>
                        <Plus className="mr-2 h-4 w-4" />
                        Add Account
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
    );
}
