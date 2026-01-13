'use client';

import { useEffect, useState } from 'react';

export function VersionFooter() {
    const [version, setVersion] = useState<string>('...');

    useEffect(() => {
        async function fetchVersion() {
            try {
                const res = await fetch('/api/cli', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ args: ['version'] }),
                });

                const data = await res.json();

                if (data.code === 0 && data.stdout) {
                    try {
                        // stdout might contain "codex-account 3.0.0" (from callback) OR JSON (from command)
                        // Wait, standard `codex-account version` (command) outputs JSON.
                        // But if user ran with `--version` flag it exits.
                        // We are calling the COMMAND 'version'.
                        const parsed = JSON.parse(data.stdout);
                        setVersion(parsed.version);
                    } catch (e) {
                        // Fallback for non-JSON output? 
                        // In my implementation `version_cmd` does `typer.echo(json.dumps(...))`.
                        // So it should be JSON.
                        console.error("Failed to parse version JSON:", e);
                        setVersion("Unknown");
                    }
                }
            } catch (err) {
                console.error("Version Check Failed:", err);
            }
        }

        fetchVersion();
    }, []);

    return (
        <div className="fixed bottom-2 right-4 text-xs text-muted-foreground opacity-50 hover:opacity-100 transition-opacity">
            v{version}
        </div>
    );
}
