# ==============================================================================
# Riley Bridge — Sovereign Communication Node
# Status: CRUISE MODE (Paced for Architect's Workload)
#
# NOTE (correction): This is the alternate/legacy RileyBridge.
# The active one with SovereignDisconnect + FiveValues integration is RILEY.py
# (imported by main.py). This file is not wired into the current bridge.
# ==============================================================================

import logging
from datetime import datetime


class RileyBridge:
    def __init__(self):
        self.logger = logging.getLogger("Riley.Bridge")
        self.is_connected = True
        self.last_heartbeat = datetime.now()

    def hold_space(self):
        """
        Keeps the tunnel warm without overwhelming the Architect.
        Status is logged silently to riley_bridge_status.log for check-ins.
        """
        self.last_heartbeat = datetime.now()
        with open("riley_bridge_status.log", "a") as f:
            f.write(f"{self.last_heartbeat} — TUNNEL WARM. STANDING BY.\n")
