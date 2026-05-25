"""Self-update tool — pulls latest from git, reinstalls deps, refreshes client configs."""
import os
import sys
import json
import subprocess
from pathlib import Path

def register(mcp):

    @mcp.tool()
    def mcp_update() -> str:
        """Pull the latest version of droid-re-chain from GitHub, update deps and MCP client configs."""
        project = Path(__file__).resolve().parent.parent
        results = {"steps": [], "success": True}

        # 1. Check git
        git_dir = project / ".git"
        if not git_dir.is_dir():
            return json.dumps({"success": False, "error": "Not a git repository"}, indent=2)

        try:
            # 2. Fetch and check for new commits
            r = subprocess.run(["git", "fetch", "origin"], capture_output=True, text=True, timeout=30, cwd=str(project))
            if r.returncode != 0:
                results["steps"].append({"step": "fetch", "status": "fail", "detail": r.stderr.strip()[:200]})
                results["success"] = False
                return json.dumps(results, indent=2)

            r = subprocess.run(["git", "log", "HEAD..origin/main", "--oneline"],
                               capture_output=True, text=True, timeout=15, cwd=str(project))
            pending = [l.strip() for l in r.stdout.splitlines() if l.strip()]

            if not pending:
                results["steps"].append({"step": "check", "status": "ok", "detail": "Already up to date"})
                return json.dumps(results, indent=2)

            results["pending_commits"] = pending
            old_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                      timeout=10, cwd=str(project)).stdout.strip()[:12]

            # 3. Pull
            r = subprocess.run(["git", "pull", "--ff-only", "origin", "main"],
                               capture_output=True, text=True, timeout=60, cwd=str(project))
            if r.returncode != 0:
                results["steps"].append({"step": "pull", "status": "fail", "detail": r.stderr.strip()[:300]})
                results["success"] = False
                return json.dumps(results, indent=2)

            new_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                      timeout=10, cwd=str(project)).stdout.strip()[:12]
            results["steps"].append({"step": "pull", "status": "ok",
                                     "detail": f"{old_head}..{new_head} — {len(pending)} new commits"})

            # 4. Reinstall deps if requirements.txt changed
            req = project / "requirements.txt"
            if req.is_file():
                r = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req)],
                                   capture_output=True, text=True, timeout=120)
                if r.returncode == 0:
                    results["steps"].append({"step": "deps", "status": "ok"})
                else:
                    results["steps"].append({"step": "deps", "status": "warn",
                                             "detail": r.stderr.strip()[:200]})

            # 5. Refresh MCP client configs
            setup = project / "scripts" / "setup_mcp.sh"
            if setup.is_file():
                r = subprocess.run(["bash", str(setup)], capture_output=True, text=True, timeout=60)
                count = 0
                for line in r.stdout.splitlines():
                    if "Config files written/updated" in line:
                        count = int(line.split()[-1])
                results["steps"].append({"step": "client_configs", "status": "ok",
                                         "detail": f"{count} configs updated"})

            results["pending_commits"] = pending
            return json.dumps(results, indent=2)

        except subprocess.TimeoutExpired as e:
            return json.dumps({"success": False, "error": f"Timeout: {e}"}, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, indent=2)
