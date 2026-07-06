from __future__ import annotations

import json
import logging
import asyncio
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import WorkflowDefinition
from app.utils.config import get_settings
from app.api.dependencies import _require_api_key

router = APIRouter(tags=["Workflow Builder"])
settings = get_settings()
logger = logging.getLogger(__name__)

WORKFLOWS_DIR = settings.data_path / "workflows"
WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/workflows",
    summary="Save or update a workflow definition",
)
async def save_workflow(workflow: WorkflowDefinition) -> dict:
    """Save a workflow definition to disk as a JSON file."""
    try:
        from datetime import datetime, timezone
        workflow.updated_at = datetime.now(timezone.utc)
        filepath = WORKFLOWS_DIR / f"{workflow.workflow_id}.json"
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(workflow.model_dump_json(indent=2))
        logger.info(
            "Workflow saved",
            extra={"name": workflow.name, "workflow_id": workflow.workflow_id},
        )
        return {"status": "saved", "workflow_id": workflow.workflow_id}
    except Exception as exc:
        logger.error("Failed to save workflow", extra={"error": str(exc)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save workflow. Check server logs for details.",
        )


@router.get(
    "/workflows",
    summary="List all saved workflow definitions",
)
async def list_workflows() -> list[dict]:
    """List all saved workflows from disk."""
    workflows = []
    try:
        for p in WORKFLOWS_DIR.glob("*.json"):
            async with aiofiles.open(p, "r", encoding="utf-8") as f:
                content = await f.read()
                workflows.append(json.loads(content))
        # Sort by updated_at desc
        workflows.sort(key=lambda w: w.get("updated_at", ""), reverse=True)
        return workflows
    except Exception as exc:
        logger.error("Failed to list workflows", extra={"error": str(exc)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list workflows. Check server logs for details.",
        )


@router.get(
    "/workflows/{workflow_id}",
    summary="Get a specific workflow definition",
)
async def get_workflow(workflow_id: str) -> dict:
    """Retrieve a specific workflow definition from disk."""
    filepath = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    try:
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)
    except Exception as exc:
        logger.error("Failed to load workflow", extra={"error": str(exc)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load workflow. Check server logs for details.",
        )


@router.delete(
    "/workflows/{workflow_id}",
    summary="Delete a saved workflow",
    dependencies=[Depends(_require_api_key)],
)
async def delete_workflow(workflow_id: str) -> dict:
    """Delete a workflow definition and its associated executions."""
    filepath = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    try:
        filepath.unlink()
        # Clean up history if any
        exec_file = WORKFLOWS_DIR / f"executions_{workflow_id}.jsonl"
        if exec_file.exists():
            exec_file.unlink()
        logger.info(f"Deleted workflow {workflow_id}")
        return {"status": "deleted", "workflow_id": workflow_id}
    except Exception as exc:
        logger.error("Failed to delete workflow", extra={"error": str(exc)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workflow. Check server logs for details.",
        )


@router.post(
    "/workflows/{workflow_id}/execute",
    summary="Execute a workflow definition against a user query",
)
async def execute_workflow_route(workflow_id: str, query: str) -> dict:
    """Load workflow and execute using workflow_executor."""
    from app.services.workflow_executor import execute_workflow
    
    filepath = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    
    try:
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            content = await f.read()
            workflow = WorkflowDefinition.model_validate_json(content)
    except Exception as exc:
        logger.error("Failed to parse workflow", extra={"error": str(exc)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse workflow. Check server logs for details.",
        )

    # Execute workflow synchronously in an executor thread
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None, lambda: execute_workflow(workflow, query)
        )
        
        # Persist execution history
        exec_file = WORKFLOWS_DIR / f"executions_{workflow_id}.jsonl"
        async with aiofiles.open(exec_file, "a", encoding="utf-8") as f:
            await f.write(result.model_dump_json() + "\n")
            
        return result.model_dump(mode="json")
    except Exception as exc:
        logger.error(f"Workflow execution failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow execution failed. Check server logs for details.",
        )


@router.get(
    "/workflows/{workflow_id}/executions",
    summary="Retrieve execution history for a workflow",
)
async def get_workflow_executions(workflow_id: str, limit: int = 50) -> dict:
    """Retrieve list of past execution results for a workflow."""
    exec_file = WORKFLOWS_DIR / f"executions_{workflow_id}.jsonl"
    executions = []
    if exec_file.exists():
        try:
            async with aiofiles.open(exec_file, "r", encoding="utf-8") as f:
                async for line in f:
                    stripped = line.strip()
                    if stripped:
                        executions.append(json.loads(stripped))
        except Exception as exc:
            logger.error(f"Failed to load executions for {workflow_id}: {exc}")
            
    # Sort descending by completed_at/started_at
    executions.sort(key=lambda e: e.get("started_at", ""), reverse=True)
    return {
        "workflow_id": workflow_id,
        "total": len(executions),
        "executions": executions[:limit],
    }
