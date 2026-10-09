import os
import subprocess
from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from typing import Optional

router = APIRouter(prefix="/webhook", tags=["Webhook"])

# A simple hardcoded secret for now (you can change this to match GitHub's secret payload signature later)
WEBHOOK_SECRET = "superfastmaxwell2026"

def run_update_script():
    # The deploy script is at the root of the project: deploy/update_server.sh
    # We use nohup to run it detached so the server can restart without killing the script
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../deploy/update_server.sh"))
    
    # We sleep 2 seconds before running to allow the HTTP response to be sent back to GitHub
    command = f"sleep 2 && bash {script_path} > /tmp/deploy.log 2>&1"
    
    subprocess.Popen(["nohup", "bash", "-c", command], preexec_fn=os.setsid)

@router.post("/github")
def github_webhook(background_tasks: BackgroundTasks, x_hub_signature_256: Optional[str] = Header(None)):
    # Note: For true security, you should verify the x_hub_signature_256 using HMAC and WEBHOOK_SECRET.
    # For now, we just blindly trigger the deploy script. GitHub will hit this URL on push.
    # To secure it quickly, you could also add a query param token like ?token=secret
    
    background_tasks.add_task(run_update_script)
    return {"status": "Deploy queued"}

@router.post("/deploy")
def manual_deploy(token: str, background_tasks: BackgroundTasks):
    if token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid token")
        
    background_tasks.add_task(run_update_script)
    return {"status": "Deploy queued"}
