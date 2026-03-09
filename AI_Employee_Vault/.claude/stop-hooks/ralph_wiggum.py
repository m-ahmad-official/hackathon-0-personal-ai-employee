#!/usr/bin/env python3
"""
Ralph Wiggum Stop Hook - Enables autonomous task completion
Prevents Claude from exiting until task is actually complete.

Gold Tier Phase 1: File-based completion detection
"""

import os
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any

def load_state(state_file: Path) -> Dict[str, Any]:
    """Load loop state from file."""
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state_file: Path, state: Dict[str, Any]):
    """Save loop state to file."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

def check_task_completion(vault_path: Path, task_id: str) -> bool:
    """
    Check if the task is complete by looking for file movement.
    Expected: Task moves from /Plans/ to /Done/
    """
    plans_dir = vault_path / "Plans"
    done_dir = vault_path / "Done"

    if not done_dir.exists():
        return False

    # Check if plan was moved to Done
    done_files = list(done_dir.glob(f"PLAN_{task_id}*.md"))
    done_files.extend(list(done_dir.glob(f"*{task_id}*.md")))

    if done_files:
        return True

    # Also check if approval task completed (moved to Done)
    approval_files = list(done_dir.glob(f"APPROVAL_*{task_id}*.md"))
    if approval_files:
        return True

    return False

def get_pending_items_count(vault_path: Path) -> int:
    """Count items in Needs_Action."""
    needs_action = vault_path / "Needs_Action"
    if needs_action.exists():
        return len([f for f in needs_action.iterdir() if f.suffix == '.md'])
    return 0

def on_stop(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main stop hook handler.
    Called when Claude attempts to exit.

    Returns:
        {"action": "continue", "reason": "..."} to block exit
        {"action": "exit", "reason": "..."} to allow exit
    """
    # Default vault location (can be configured via params)
    vault_path = Path(os.getenv("VAULT_PATH", "AI_Employee_Vault"))
    state_file = vault_path / ".claude" / "loop_state.json"

    # Load state
    state = load_state(state_file)

    # Check if loop is active
    is_looping = state.get("looping", False)
    max_iterations = state.get("max_iterations", 10)
    current_iteration = state.get("current_iteration", 0)
    task_id = state.get("task_id", "unknown")

    # If not looping, allow exit
    if not is_looping:
        return {
            "action": "exit",
            "reason": "Ralph Wiggum loop not active"
        }

    # Increment iteration
    current_iteration += 1
    state["current_iteration"] = current_iteration

    # Check max iterations
    if current_iteration >= max_iterations:
        save_state(state_file, {**state, "looping": False})
        return {
            "action": "exit",
            "reason": f"Reached max iterations ({max_iterations})"
        }

    # Check task completion
    if check_task_completion(vault_path, task_id):
        save_state(state_file, {**state, "looping": False, "completed": True})
        return {
            "action": "exit",
            "reason": f"Task {task_id} completed (found in Done folder)"
        }

    # Check if there's still work in Needs_Action
    pending_count = get_pending_items_count(vault_path)
    if pending_count > 0:
        # Keep looping
        save_state(state_file, state)
        return {
            "action": "continue",
            "reason": f"Task not complete. {pending_count} item(s) still need processing. Iteration {current_iteration}/{max_iterations}"
        }

    # No pending items but task not marked complete?
    # Could be "monitoring" mode - check if we should exit
    if pending_count == 0:
        # Wait a bit more in case something is processing
        if current_iteration < 3:
            save_state(state_file, state)
            return {
                "action": "continue",
                "reason": f"No pending items but task not marked complete. Wait... (iteration {current_iteration})"
            }
        else:
            save_state(state_file, {**state, "looping": False})
            return {
                "action": "exit",
                "reason": "No pending work found"
            }

    # Default: continue
    save_state(state_file, state)
    return {
        "action": "continue",
        "reason": f"Continuing loop (iteration {current_iteration})"
    }

# Entry point for standalone testing
if __name__ == "__main__":
    # Simulate stop hook call
    test_params = {
        "loop_active": True,
        "task_id": "test123",
        "max_iterations": 10
    }

    result = on_stop(test_params)
    print(f"Action: {result['action']}")
    print(f"Reason: {result['reason']}")
