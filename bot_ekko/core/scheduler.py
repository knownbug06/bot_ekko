import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from bot_ekko.core.logger import get_logger

logger = get_logger("Scheduler")

class Scheduler:
    """
    Manages scheduled events and state transitions based on time.
    """
    def __init__(self, schedule_file: str):
        """
        Initialize the Scheduler.

        Args:
            schedule_file (str): Path to the JSON schedule file.
        """
        self.schedule_file = schedule_file
        self.events: List[Dict] = []
        self.load_schedule()

    def load_schedule(self) -> None:
        """
        Loads the schedule from the JSON file. 
        Populates self.events with sorted events by priority.
        """
        try:
            with open(self.schedule_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.events = data
                elif isinstance(data, dict):
                     self.events = data.get("events", [])
                
                # Sort by priority (descending). Default priority 0 if not set.
                self.events.sort(key=lambda x: x.get("priority", 0), reverse=True)
                
                logger.info(f"Loaded {len(self.events)} scheduled events.")
        except FileNotFoundError:
            logger.error(f"Schedule file not found: {self.schedule_file}")
            self.events = []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing schedule file: {e}")
            self.events = []

    def get_target_state(self, now_dt: datetime, current_state: str) -> Optional[Tuple[str, Optional[Dict]]]:
        """
        Checks if any scheduled event is active AND if the current state allows interruption.
        
        Args:
            now_dt (datetime): Current datetime.
            current_state (str): Name of the current state.

        Returns:
            Optional[Tuple[str, Optional[Dict]]]: (target_state, params) if conditions are met, else None.
        """
        for event in self.events:
            target_state = event.get("state")
            params = event.get("params")
            # name = event.get("name") # unused
            # priority = event.get("priority", 10) # unused here as list is sorted
            
            # 1. Check time window
            if not self._is_event_active(event, now_dt):
                continue
                
            # 2. Check overlap (already in state)
            if current_state == target_state:
                # We are already in the target state, keep it.
                return target_state, params
                
            # 3. Check if current state is interruptible by this event
            interruptible = set(event.get("interruptible_states", []))
            
            # Default fallback: if not specified, assume it can interrupt standard states
            if not interruptible:
                 interruptible = {"ACTIVE", "SQUINTING", "THINKING", "SLEEPING", "WAKING"}
                 
            if current_state in interruptible:
                return target_state, params
                
        return None

    def _is_event_active(self, event: Dict, now_dt: datetime) -> bool:
        event_type = event.get("type")
        if event_type == "daily":
            return self._check_daily_interval(event, now_dt)
        elif event_type == "date":
            return self._check_date_interval(event, now_dt)
        elif event_type == "hourly":
            return self._check_hourly_interval(event, now_dt)
        return False

    def _check_date_interval(self, event: Dict, now_dt: datetime) -> bool:
        start_str = event.get("start_datetime")
        end_str = event.get("end_datetime")
        
        if not start_str or not end_str:
            return False
            
        try:
            # Expected format: YYYY-MM-DD HH:MM:SS
            start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
            
            return start_dt <= now_dt < end_dt
        except ValueError:
            logger.error(f"Invalid datetime format in event {event.get('name')}. Use YYYY-MM-DD HH:MM:SS")
            return False

    def _check_daily_interval(self, event: Dict, now_dt: datetime) -> bool:
        start_str = event.get("start_time")
        end_str = event.get("end_time")
        
        if not start_str or not end_str:
            return False

        try:
            start_h, start_m = map(int, start_str.split(':'))
            end_h, end_m = map(int, end_str.split(':'))
            
            curr_total = now_dt.hour * 60 + now_dt.minute
            start_total = start_h * 60 + start_m
            end_total = end_h * 60 + end_m
            
            if start_total > end_total: # Spans midnight
                return curr_total >= start_total or curr_total < end_total
            else: # Same day
                return start_total <= curr_total < end_total
                
        except ValueError:
            logger.error(f"Invalid time format in event {event.get('name')}")
            return False

    def _check_hourly_interval(self, event: Dict, now_dt: datetime) -> bool:
        """
        Active if current minute/second is within the first 'duration' seconds of the hour.
        Default duration 10s.
        """
        params = event.get("params", {})
        duration = params.get("duration", 10) # seconds
        
        # Check if we are in the first 'duration' seconds of the hour
        # e.g. 10:00:00 to 10:00:10
        
        seconds_since_hour = now_dt.minute * 60 + now_dt.second
        return seconds_since_hour < duration

