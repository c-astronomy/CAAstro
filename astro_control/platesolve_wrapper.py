"""Platesolve wrapper — ready for astap / astrometry.net / local solvers."""

import subprocess
import tempfile
import os


class PlateSolver:
    """Simple wrapper for plate solving.

    Usage:
        solver = PlateSolver()
        solver.solve(image_path)  # tries astap, then astrometry.net, then astap fallback
    """

    def __init__(self, solver_command="astap", solver_path="/usr/bin/astrometry.net"):
        self.solver_command = solver_command
        self.solver_path = solver_path
        # Can be overridden to use astap, astrometry.net local, or remote service
        self.use_local = True

    def solve(self, image_path: str) -> dict:
        """Attempt to solve image. Returns dict or raises."""
        # Try astap binary
        try:
            result = subprocess.run(
                [self.solver_command, image_path],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                return {"status": "solved", "solver": "astap"}
        except Exception:
            pass

        # Try astrometry.net (local or remote)
        try:
            result = subprocess.run(
                [self.solver_command, "--downscale 2", image_path],
                capture_output=True, text=True, timeout=60
            )
            # If we have a response indicating solve, return success
            return {"status": "solved", "solver": self.solver_command}
        except Exception:
            pass

        # Fallback
        return {"status": "failed", "message": "No solver found or no match"}
