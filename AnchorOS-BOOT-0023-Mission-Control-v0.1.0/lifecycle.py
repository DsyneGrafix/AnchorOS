from enum import Enum


class LifecycleState(Enum):
    DISCOVERED = "Discovered"
    REGISTERED = "Registered"
    INITIALIZED = "Initialized"
    STARTING = "Starting"
    RUNNING = "Running"
    STOPPING = "Stopping"
    STOPPED = "Stopped"
    FAILED = "Failed"
