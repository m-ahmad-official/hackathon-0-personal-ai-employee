#!/usr/bin/env python3
"""
Scheduler - Silver Tier Component

Cron-based task scheduler for AI Employee automated workflows.

Features:
- Cron expression support (every 5 minutes, daily at 9am, etc.)
- Execute Claude Code skills via command line
- Task logging and monitoring
- Configuration via YAML files
- Integration with orchestrator

Usage:
  python scheduler/scheduler.py --config scheduler/config.yaml

Setup:
  1. Configure schedule in config.yaml
  2. Add to crontab: */5 * * * * cd /path/to/vault && python scheduler/scheduler.py --config scheduler/config.yaml
  OR run as daemon: python scheduler/scheduler.py --config scheduler/config.yaml --daemon
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ScheduledTask:
    """Represents a scheduled task."""

    def __init__(self, name: str, schedule: Dict[str, Any], action: Dict[str, Any]):
        """
        Initialize scheduled task.

        Args:
            name: Task name
            schedule: Dict with cron-like scheduling fields
                {
                    'minute': '*',
                    'hour': '9',
                    'day': '*',
                    'month': '*',
                    'weekday': '*'
                }
            action: Dict with action to execute
                {
                    'type': 'claude_skill' | 'command' | 'orchestrator',
                    'skill': 'skill_name',
                    'arguments': ['--arg1', 'value1'],
                    'working_dir': '/path/to/vault'
                }
        """
        self.name = name
        self.schedule = schedule
        self.action = action
        self.last_run = None
        self.last_result = None

    def should_run(self, now: datetime) -> bool:
        """
        Check if task should run at given time.

        Args:
            now: Current datetime

        Returns:
            True if task should run
        """
        # Simple cron matching
        minute_match = self._match_field(now.minute, self.schedule.get('minute', '*'))
        hour_match = self._match_field(now.hour, self.schedule.get('hour', '*'))
        day_match = self._match_field(now.day, self.schedule.get('day', '*'))
        month_match = self._match_field(now.month, self.schedule.get('month', '*'))
        weekday_match = self._match_field(now.isoweekday(), self.schedule.get('weekday', '*'), wrap=1)

        return minute_match and hour_match and day_match and month_match and weekday_match

    def _match_field(self, value: int, pattern: str, wrap: int = None) -> bool:
        """
        Match a field value against cron pattern.

        Args:
            value: Field value (0-59 for minutes, 0-23 for hours, etc.)
            pattern: Cron pattern (*, number, range, list)
            wrap: Max value + 1 (for minutes=60, hours=24, weekday=7)

        Returns:
            True if matches
        """
        if pattern == '*':
            return True

        # Handle comma-separated lists
        if ',' in pattern:
            for part in pattern.split(','):
                if self._match_field(value, part.strip(), wrap):
                    return True
            return False

        # Handle ranges (e.g., "9-17")
        if '-' in pattern:
            start, end = pattern.split('-')
            start_val = int(start)
            end_val = int(end)
            if wrap and end_val < start_val:
                # Wrap around (e.g., "22-2" for 22:00-02:00)
                return value >= start_val or value <= end_val
            else:
                return start_val <= value <= end_val

        # Handle step values (e.g., "*/5" for every 5)
        if '/' in pattern:
            base, step = pattern.split('/')
            if base != '*':
                base_val = int(base)
                # Complex - not fully implemented for brevity
                return value >= base_val and (value - base_val) % int(step) == 0
            else:
                # "*/5" means every 5 units
                return value % int(step) == 0

        # Single value
        try:
            return value == int(pattern)
        except ValueError:
            logger.warning(f"Invalid pattern: {pattern}")
            return False

    def execute(self) -> bool:
        """
        Execute the task action.

        Returns:
            True if successful, False otherwise
        """
        self.last_run = datetime.now()
        action_type = self.action.get('type', 'command')
        working_dir = self.action.get('working_dir', '.')

        try:
            if action_type == 'claude_skill':
                # Execute Claude skill via claude command
                skill = self.action.get('skill')
                args = self.action.get('arguments', [])
                cmd = ['claude', '--print'] + [f'/skill {skill}'] + args

                logger.info(f"Executing skill: {skill}")
                result = subprocess.run(
                    cmd,
                    cwd=working_dir,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )

                if result.returncode == 0:
                    logger.info(f"Task {self.name} completed successfully")
                    self.last_result = {'success': True, 'output': result.stdout}
                    return True
                else:
                    logger.error(f"Task {self.name} failed: {result.stderr}")
                    self.last_result = {'success': False, 'error': result.stderr}
                    return False

            elif action_type == 'command':
                # Execute arbitrary command
                cmd = self.action.get('command')
                if isinstance(cmd, list):
                    result = subprocess.run(
                        cmd,
                        cwd=working_dir,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                else:
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        cwd=working_dir,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )

                if result.returncode == 0:
                    logger.info(f"Task {self.name} completed successfully")
                    self.last_result = {'success': True, 'output': result.stdout}
                    return True
                else:
                    logger.error(f"Task {self.name} failed: {result.stderr}")
                    self.last_result = {'success': False, 'error': result.stderr}
                    return False

            elif action_type == 'orchestrator':
                # Trigger orchestrator to process Needs_Action
                vault = self.action.get('vault', working_dir)
                cmd = ['python', 'orchestrator.py', '--vault', vault, '--process-now']

                logger.info(f"Running orchestrator for vault: {vault}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout for orchestrator
                )

                if result.returncode == 0:
                    logger.info(f"Orchestrator completed for {self.name}")
                    self.last_result = {'success': True, 'output': result.stdout}
                    return True
                else:
                    logger.error(f"Orchestrator failed: {result.stderr}")
                    self.last_result = {'success': False, 'error': result.stderr}
                    return False

            else:
                logger.error(f"Unknown action type: {action_type}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Task {self.name} timed out")
            self.last_result = {'success': False, 'error': 'Timeout'}
            return False
        except Exception as e:
            logger.error(f"Task {self.name} crashed: {e}")
            self.last_result = {'success': False, 'error': str(e)}
            return False


class Scheduler:
    """Main scheduler class."""

    def __init__(self, config_path: str):
        """
        Initialize scheduler.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.tasks: List[ScheduledTask] = []
        self.running = False
        self.check_interval = 60  # Check every 60 seconds

        self._load_config()

    def _load_config(self):
        """Load tasks from configuration file."""
        if not self.config_path.exists():
            logger.error(f"Config file not found: {self.config_path}")
            raise FileNotFoundError(f"Config file: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Global config
        self.check_interval = config.get('check_interval', 60)
        default_working_dir = config.get('default_working_dir', '.')

        # Load tasks
        for task_config in config.get('tasks', []):
            name = task_config['name']
            schedule = task_config['schedule']
            action = task_config['action']

            # Set default working dir if not specified
            if 'working_dir' not in action:
                action['working_dir'] = default_working_dir

            task = ScheduledTask(name, schedule, action)
            self.tasks.append(task)
            logger.info(f"Loaded task: {name} - {schedule} → {action['type']}")

        logger.info(f"Loaded {len(self.tasks)} tasks")

    def run_once(self) -> int:
        """
        Check all tasks and run those that are due.

        Returns:
            Number of tasks executed
        """
        now = datetime.now()
        executed = 0

        for task in self.tasks:
            if task.should_run(now):
                logger.info(f"Task due: {task.name}")
                success = task.execute()
                if success:
                    executed += 1
                else:
                    logger.error(f"Task {task.name} failed execution")

        return executed

    def run_daemon(self):
        """Run scheduler as daemon, checking tasks periodically."""
        logger.info("Scheduler daemon started")
        logger.info(f"Checking every {self.check_interval} seconds")
        self.running = True

        try:
            while self.running:
                executed = self.run_once()
                if executed > 0:
                    logger.info(f"Executed {executed} tasks in this cycle")
                else:
                    logger.debug("No tasks due")

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler crashed: {e}")
            raise

    def stop(self):
        """Stop the daemon."""
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="Scheduler for AI Employee")
    parser.add_argument(
        '--config',
        default='scheduler/config.yaml',
        help='Path to scheduler config YAML (default: scheduler/config.yaml)'
    )
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as daemon (continuous check loop)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run due tasks once and exit'
    )

    args = parser.parse_args()

    try:
        scheduler = Scheduler(args.config)

        if args.once:
            # Run once and exit
            executed = scheduler.run_once()
            print(f"\n✅ Executed {executed} tasks")
            return 0
        else:
            # Run as daemon (default)
            scheduler.run_daemon()
            return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
