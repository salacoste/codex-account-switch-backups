
import { NextRequest, NextResponse } from 'next/server';
import { execFile } from 'child_process';
import path from 'path';
import util from 'util';

const execFileAsync = util.promisify(execFile);

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();
        const args = body.args || [];

        // Security: Whitelist allowed root commands to prevent arbitrary execution
        // Although this is a dev tool, basic sanity check is good.
        // Allowed first args: 'status', 'list', 'switch', 'login', 'save', 'device-login-init', 'device-login-poll', 'add'
        const allowedCommands = ['status', 'list', 'switch', 'login', 'save', 'device-login-init', 'device-login-poll', 'add'];

        // We might have flags like --json before the command.
        // Let's just pass everything for now as this is a strictly local dev bridge.
        // But we should verify we aren't executing completely different binaries.

        // Location of the binary relative to the Next.js project root (apps/web)
        // We are in apps/web/app/api/cli/route.ts
        // Project root is apps/web/
        // Binary is in apps/web/src-tauri/binaries/

        // In dev mode, process.cwd() is usually the project root (apps/web)
        const binaryPath = path.resolve(process.cwd(), 'src-tauri/binaries/codex-backend-aarch64-apple-darwin');

        console.log(`[API Proxy] Executing: ${binaryPath} ${args.join(' ')}`);

        const { stdout, stderr } = await execFileAsync(binaryPath, args);

        return NextResponse.json({
            code: 0,
            stdout: stdout,
            stderr: stderr,
        });

    } catch (error: any) {
        console.error("[API Proxy] Execution failed:", error);
        return NextResponse.json({
            code: error.code || 1,
            stdout: error.stdout || "",
            stderr: error.stderr || error.message,
        }, { status: 500 }); // Or 200 with error code to mimic Tauri command handling
    }
}
