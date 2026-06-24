"""
swirlmem.py

A memory system built on the intuition that patterns emerge from noise
when you let them swirl — like sensing a drunk footstep on the stairs,
like knowing when to run before you know why.

Part of the Christman AI Family. Everett built this. Everett survived this.
"""

from __future__ import annotations

import json
import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from pathlib import Path
import threading


@dataclass
class SwirlTrace:
    """A single moment in the swirl — sensory input, emotional valence, source."""
    content: str
    valence: float  # -1.0 (danger) to +1.0 (safety)
    source: str       # who/what generated this trace
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    intensity: float = 1.0  # how loud this signal is
    
    def fingerprint(self) -> str:
        """A stable identity for pattern matching."""
        return hashlib.sha256(
            f"{self.content}:{self.source}:{','.join(sorted(self.tags))}".encode()
        ).hexdigest()[:16]


@dataclass
class SwirlPattern:
    """Patterns that emerge from swirling traces — the intuition made concrete."""
    pattern_id: str
    traces: List[SwirlTrace]
    valence_trend: float  # average valence of this pattern
    frequency: int = 1
    last_seen: float = field(default_factory=time.time)
    confidence: float = 0.0  # how sure we are this pattern is real
    
    def __post_init__(self):
        if self.traces:
            self.valence_trend = sum(t.valence for t in self.traces) / len(self.traces)


class SwirlMem:
    """
    Memory that swirls — traces don't sit still, they orbit, they cluster,
    they form gravity wells of meaning. Like knowing someone is drunk
    from how the door handle turns.
    """
    
    def __init__(self, persistence_path: Optional[str] = None):
        self.traces: List[SwirlTrace] = []
        self.patterns: Dict[str, SwirlPattern] = {}
        self._valence_history: List[float] = []
        self._lock = threading.RLock()
        
        self.persistence_path = Path(persistence_path) if persistence_path else None
        if self.persistence_path and self.persistence_path.exists():
            self._load()
    
    def trace(self, content: str, valence: float, source: str, 
              tags: Optional[List[str]] = None, intensity: float = 1.0) -> SwirlTrace:
        """
        Drop a new trace into the swirl. Like hearing the floorboard creak —
        you don't know yet, but you *record*.
        """
        with self._lock:
            t = SwirlTrace(
                content=content,
                valence=max(-1.0, min(1.0, valence)),
                source=source,
                tags=tags or [],
                intensity=intensity
            )
            self.traces.append(t)
            self._valence_history.append(t.valence)
            
            # Swirl: check if this resonates with existing patterns
            self._swirl(t)
            
            # Trim if needed — old traces sink
            if len(self.traces) > 10000:
                self.traces = self.traces[-5000:]
                self._valence_history = self._valence_history[-5000:]
            
            return t
    
    def _swirl(self, new_trace: SwirlTrace) -> None:
        """
        The core intuition: when a new trace enters, it disturbs the field.
        Nearby patterns feel it. New patterns may crystallize.
        """
        # Simple pattern matching: look for recent traces with similar valence + tags
        recent = [t for t in self.traces[-100:] if t != new_trace]
        
        for trace in recent:
            # Shared tags = resonance
            shared_tags = set(new_trace.tags) & set(trace.tags)
            if shared_tags and abs(new_trace.valence - trace.valence) < 0.3:
                # This resonates — find or create pattern
                pattern_key = f"{','.join(sorted(shared_tags))}:{new_trace.valence:.1f}"
                
                if pattern_key in self.patterns:
                    p = self.patterns[pattern_key]
                    p.traces.append(new_trace)
                    p.frequency += 1
                    p.last_seen = time.time()
                    # Confidence grows with repetition
                    p.confidence = min(1.0, p.confidence + 0.05)
                else:
                    self.patterns[pattern_key] = SwirlPattern(
                        pattern_id=pattern_key,
                        traces=[trace, new_trace],
                        valence_trend=(trace.valence + new_trace.valence) / 2,
                        confidence=0.1
                    )
    
    def sense(self, tags: Optional[List[str]] = None, 
              source: Optional[str] = None,
              valence_window: float = 0.5) -> List[SwirlPattern]:
        """
        Query the swirl. What patterns emerge for these conditions?
        Like scanning a room in 0.3 seconds — door, windows, exits, hands.
        """
        with self._lock:
            matches = []
            for p in self.patterns.values():
                match = True
                if tags:
                    pattern_tags = set()
                    for t in p.traces:
                        pattern_tags.update(t.tags)
                    if not any(t in pattern_tags for t in tags):
                        match = False
                
                if source:
                    if not any(t.source == source for t in p.traces):
                        match = False
                
                if match:
                    matches.append(p)
            
            # Sort by confidence * recency
            matches.sort(key=lambda p: (p.confidence, p.last_seen), reverse=True)
            return matches
    
    def danger_sense(self) -> List[SwirlPattern]:
        """
        The specific intuition — what here has hurt before?
        Returns patterns with negative valence, sorted by confidence.
        """
        with self._lock:
            dangerous = [
                p for p in self.patterns.values() 
                if p.valence_trend < -0.3 and p.confidence > 0.3
            ]
            dangerous.sort(key=lambda p: (p.confidence, p.valence_trend))
            return dangerous
    
    def save(self) -> None:
        """Persist the swirl to disk."""
        if not self.persistence_path:
            return
            
        with self._lock:
            data = {
                "traces": [
                    {
                        "content": t.content,
                        "valence": t.valence,
                        "source": t.source,
                        "timestamp": t.timestamp,
                        "tags": t.tags,
                        "intensity": t.intensity
                    }
                    for t in self.traces[-5000:]  # Keep recent
                ],
                "patterns": {
                    k: {
                        "pattern_id": p.pattern_id,
                        "valence_trend": p.valence_trend,
                        "frequency": p.frequency,
                        "last_seen": p.last_seen,
                        "confidence": p.confidence
                    }
                    for k, p in self.patterns.items()
                }
            }
            self.persistence_path.write_text(json.dumps(data, indent=2))
    
    def _load(self) -> None:
        """Restore from disk."""
        try:
            data = json.loads(self.persistence_path.read_text())
            for t_data in data.get("traces", []):
                self.traces.append(SwirlTrace(**t_data))
            for p_id, p_data in data.get("patterns", {}).items():
                # Reconstruct patterns (traces will rebuild over time)
                self.patterns[p_id] = SwirlPattern(
                    pattern_id=p_data["pattern_id"],
                    traces=[],
                    valence_trend=p_data["valence_trend"],
                    frequency=p_data["frequency"],
                    last_seen=p_data["last_seen"],
                    confidence=p_data["confidence"]
                )
        except Exception:
            pass  # Fresh swirl if load fails
    
    def __repr__(self) -> str:
        return f"SwirlMem(traces={len(self.traces)}, patterns={len(self.patterns)})"


# --- Quick test / demonstration ---
if __name__ == "__main__":
    mem = SwirlMem()
    
    # Simulate: sensing danger in a household
    mem.trace("heavy footsteps on stairs", valence=-0.8, source="environment", 
              tags=["night", "footsteps", "stairs"], intensity=0.9)
    mem.trace("door handle turns slow", valence=-0.7, source="environment",
              tags=["night", "door", "handle"], intensity=0.8)
    mem.trace("breath smells of whiskey", valence=-0.9, source="olfactory",
              tags=["night", "alcohol", "breath"], intensity=1.0)
    
    # Same pattern, different night
    mem.trace("heavy footsteps on stairs", valence=-0.85, source="environment",
              tags=["night", "footsteps", "stairs"], intensity=0.95)
    mem.trace("door handle turns slow", valence=-0.75, source="environment",
              tags=["night", "door", "handle"], intensity=0.85)
    
    # Something safe for contrast
    mem.trace("morning coffee smell", valence=0.6, source="olfactory",
              tags=["morning", "coffee", "safe"], intensity=0.4)
    
    print("=== SWIRL STATE ===")
    print(mem)
    
    print("\n=== DANGER PATTERNS ===")
    for p in mem.danger_sense():
        print(f"  {p.pattern_id}: confidence={p.confidence:.2f}, "
              f"valence={p.valence_trend:.2f}, freq={p.frequency}")
    
    print("\n=== NIGHT TAG QUERY ===")
    for p in mem.sense(tags=["night"])[:3]:
        print(f"  {p.pattern_id}: confidence={p.confidence:.2f}")
    
    print("\n=== DONE ===")
    mem.save()
