from enum import Enum


class LifecycleState(Enum):
    CREATED = "Created"
    DISCOVERED = "Discovered"
    REGISTERED = "Registered"
    STARTING = "Starting"
    RUNNING = "Running"
    STOPPING = "Stopping"
    STOPPED = "Stopped"
    FAILED = "Failed"
