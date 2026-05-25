"""Task scheduling utilities for the runtime engine."""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class ScheduleType(Enum):
    """Types of scheduling strategies."""
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    CRON = "cron"
    INTERVAL = "interval"


@dataclass
class ScheduledTask:
    """A task scheduled for future execution."""
    task_id: str
    schedule_type: ScheduleType
    callback: Callable
    interval: Optional[timedelta] = None
    cron_expr: Optional[str] = None
    next_run: Optional[datetime] = None
    enabled: bool = True


class TaskScheduler:
    """Scheduler for managing recurring and delayed tasks."""

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task_handle: Optional[asyncio.Task] = None

    def schedule_task(
        self,
        task_id: str,
        callback: Callable,
        schedule_type: ScheduleType = ScheduleType.IMMEDIATE,
        interval: Optional[timedelta] = None,
        cron_expr: Optional[str] = None,
        delay: Optional[timedelta] = None
    ) -> ScheduledTask:
        """Schedule a task for execution."""
        if schedule_type == ScheduleType.DELAYED and delay:
            next_run = datetime.utcnow() + delay
        elif schedule_type == ScheduleType.INTERVAL and interval:
            next_run = datetime.utcnow() + interval
        else:
            next_run = datetime.utcnow()

        scheduled = ScheduledTask(
            task_id=task_id,
            schedule_type=schedule_type,
            callback=callback,
            interval=interval,
            cron_expr=cron_expr,
            next_run=next_run
        )
        self._tasks[task_id] = scheduled
        return scheduled

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = False
            return True
        return False

    async def start(self):
        """Start the scheduler loop."""
        self._running = True
        self._task_handle = asyncio.create_task(self._schedule_loop())

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task_handle:
            self._task_handle.cancel()
            try:
                await self._task_handle
            except asyncio.CancelledError:
                pass

    async def _schedule_loop(self):
        """Main scheduler loop."""
        while self._running:
            now = datetime.utcnow()
            for task in self._tasks.values():
                if task.enabled and task.next_run and now >= task.next_run:
                    asyncio.create_task(self._execute_scheduled(task))
                    self._advance_next_run(task)

            await asyncio.sleep(1)

    async def _execute_scheduled(self, task: ScheduledTask):
        """Execute a scheduled task."""
        try:
            if asyncio.iscoroutinefunction(task.callback):
                await task.callback()
            else:
                task.callback()
        except Exception:
            pass

    def _advance_next_run(self, task: ScheduledTask):
        """Calculate the next run time for a task."""
        if task.schedule_type == ScheduleType.INTERVAL and task.interval:
            task.next_run = datetime.utcnow() + task.interval
        elif task.schedule_type == ScheduleType.CRON:
            # Simplified cron handling
            task.next_run = datetime.utcnow() + timedelta(minutes=5)
        else:
            task.enabled = False
