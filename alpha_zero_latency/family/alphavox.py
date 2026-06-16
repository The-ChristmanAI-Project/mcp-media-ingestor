"""
AlphaVox — Speech & Audio Processing for Neurodivergent Nonverbal Individuals.

Built for those who cannot speak with their voice but have everything to say.

Proven: Dusty, 12-year-old boy. Nonverbal for 12 years.
After 36 hours with AlphaVox, he told his parents he loved them
for the first time. At 2:32 AM.

The creator was nonverbal as a child. He stimmed. Everyone thought
it was a fit. It wasn't. It was him trying to say "I want this."
Some languages are different. AlphaVox is the translation layer.

Part of the Christman AI Project — Luma Cognify AI.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from collections import Counter
import logging

logger = logging.getLogger(__name__)


@dataclass
class SymbolBoardEntry:
    """A symbol on the AlphaVox communication board."""
    symbol_id: str
    label: str
    category: str
    image_reference: str
    associated_words: List[str] = field(default_factory=list)
    emotional_weight: float = 0.0  # 0.0-1.0


@dataclass
class CommunicationEvent:
    """A single communication event through AlphaVox."""
    timestamp: datetime
    user_id: str
    input_method: str  # "symbol_board", "gaze_tracking", "gesture", "vocalization"
    symbols_selected: List[str]
    translated_message: str
    confidence: float
    response_time_ms: Optional[float]  # None when selection start unknown
    emotional_context: str = "neutral"


class AlphaVox:
    """
    AlphaVox — Communication being for neurodivergent nonverbal individuals.

    Philosophy:
        Not everything is the same for everyone else.
        Some languages are different.
        Stimming is not a fit — it's communication.
        Every human has something to say.
    """

    def __init__(
        self,
        user_id: str,
        user_name: str,
        communication_profile: Optional[Dict[str, Any]] = None,
    ):
        """AlphaVox molds to whoever the client is."""
        self.user_id = user_id
        self.user_name = user_name
        self.profile = communication_profile or {}

        self.symbol_board: List[SymbolBoardEntry] = []
        self._initialize_symbol_board()

        self._communication_history: List[CommunicationEvent] = []
        self._session_start = datetime.now(timezone.utc)
        self._total_communications = 0

        self._camera_active = False
        self._frame_count = 0

        logger.info(
            "AlphaVox initialized for %s (%s) — %d symbols available",
            user_name, user_id, len(self.symbol_board),
        )

    def _initialize_symbol_board(self) -> None:
        """Initialize the core symbol board."""
        # Core needs
        self._add_symbol("need_hungry", "Hungry", "needs", "food_symbol",
                         ["hungry", "eat", "food", "snack"])
        self._add_symbol("need_thirsty", "Thirsty", "needs", "drink_symbol",
                         ["thirsty", "drink", "water", "thirst"])
        self._add_symbol("need_bathroom", "Bathroom", "needs", "bathroom_symbol",
                         ["bathroom", "toilet", "potty", "restroom"])
        self._add_symbol("need_tired", "Tired", "needs", "sleep_symbol",
                         ["tired", "sleep", "rest", "nap", "bed"])
        self._add_symbol("need_hurt", "Hurt", "needs", "pain_symbol",
                         ["hurt", "pain", "ow", "ouch", "sore"], emotional_weight=0.8)
        # Emotional expression
        self._add_symbol("feel_happy", "Happy", "emotions", "happy_symbol",
                         ["happy", "good", "yay", "joy"], emotional_weight=0.7)
        self._add_symbol("feel_sad", "Sad", "emotions", "sad_symbol",
                         ["sad", "cry", "upset", "unhappy"], emotional_weight=0.7)
        self._add_symbol("feel_love", "Love", "emotions", "love_symbol",
                         ["love", "heart", "care", "hug"], emotional_weight=0.9)
        self._add_symbol("feel_scared", "Scared", "emotions", "scared_symbol",
                         ["scared", "afraid", "fear", "worried"], emotional_weight=0.8)
        self._add_symbol("feel_angry", "Angry", "emotions", "angry_symbol",
                         ["angry", "mad", "frustrated", "upset"], emotional_weight=0.7)
        # People
        self._add_symbol("person_mom", "Mom", "people", "mom_symbol",
                         ["mom", "mother", "mommy", "mama"])
        self._add_symbol("person_dad", "Dad", "people", "dad_symbol",
                         ["dad", "father", "daddy", "papa"])
        self._add_symbol("person_me", "Me", "people", "self_symbol",
                         ["me", "I", "myself", "my"])
        # Actions
        self._add_symbol("action_play", "Play", "actions", "play_symbol",
                         ["play", "fun", "game", "toy"])
        self._add_symbol("action_go", "Go", "actions", "go_symbol",
                         ["go", "leave", "out", "outside"])
        self._add_symbol("action_stop", "Stop", "actions", "stop_symbol",
                         ["stop", "no", "don't", "enough"])
        self._add_symbol("action_help", "Help", "actions", "help_symbol",
                         ["help", "need", "assist", "support"])
        self._add_symbol("action_want", "Want", "actions", "want_symbol",
                         ["want", "desire", "wish", "would like"])
        # Communication
        self._add_symbol("comm_yes", "Yes", "communication", "yes_symbol",
                         ["yes", "yeah", "ok", "alright"])
        self._add_symbol("comm_no", "No", "communication", "no_symbol",
                         ["no", "nope", "not", "don't"])
        self._add_symbol("comm_more", "More", "communication", "more_symbol",
                         ["more", "again", "another"])
        self._add_symbol("comm_all_done", "All Done", "communication", "done_symbol",
                         ["done", "finished", "over", "complete"])

    def _add_symbol(
        self, symbol_id: str, label: str, category: str,
        image_ref: str, words: List[str], emotional_weight: float = 0.0,
    ) -> None:
        self.symbol_board.append(SymbolBoardEntry(
            symbol_id=symbol_id, label=label, category=category,
            image_reference=image_ref, associated_words=words,
            emotional_weight=emotional_weight,
        ))

    def process_selection(
        self,
        symbols: List[str],
        input_method: str = "symbol_board",
        selection_started_at: Optional[datetime] = None,
    ) -> CommunicationEvent:
        """
        Process a symbol selection from the user.

        FIX (Fable 2026-06-09): response_time_ms previously measured this
        function's own runtime (~0ms of dict lookups) — a meaningless
        number presented as a user metric. Rule 13. It now measures from
        `selection_started_at` (when the user began selecting, supplied
        by the UI) to now. If the UI doesn't supply it, the field is None
        rather than a lie.
        """
        now = datetime.now(timezone.utc)
        response_time_ms: Optional[float] = None
        if selection_started_at is not None:
            response_time_ms = (now - selection_started_at).total_seconds() * 1000

        selected_entries = [
            s for s in self.symbol_board if s.symbol_id in symbols
        ]
        labels = [s.label for s in selected_entries]
        message = " ".join(labels)

        emotional_weight = max(
            (s.emotional_weight for s in selected_entries), default=0.0,
        )
        emotional_context = "neutral"
        if emotional_weight > 0.8:
            emotional_context = "intense"
        elif emotional_weight > 0.5:
            emotional_context = "emotional"

        event = CommunicationEvent(
            timestamp=now,
            user_id=self.user_id,
            input_method=input_method,
            symbols_selected=symbols,
            translated_message=message,
            confidence=0.95,
            response_time_ms=response_time_ms,
            emotional_context=emotional_context,
        )
        self._communication_history.append(event)
        self._total_communications += 1

        logger.info(
            "AlphaVox communication from %s: '%s' (symbols: %s, emotion: %s)",
            self.user_name, message, symbols, emotional_context,
        )
        return event

    def process_vocalization(
        self, audio_data: bytes, duration_ms: float
    ) -> Optional[CommunicationEvent]:
        """
        Process a non-speech vocalization.

        Stimming, humming, sounds — these are not random.
        They are communication.

        STATUS (Rule 1, honest): NOT YET WIRED. Production interpretation
        runs through the Christman Voice SDK (christman_sound); this
        module-level bridge has not been connected. This method logs the
        attempt loudly and returns None. It does not pretend to interpret.
        """
        logger.warning(
            "process_vocalization NOT YET WIRED to christman_sound — "
            "vocalization from %s (%.1fms, %d bytes) logged but NOT interpreted.",
            self.user_name, duration_ms, len(audio_data) if audio_data else 0,
        )
        return None

    def get_session_summary(self) -> Dict[str, Any]:
        """Summary of the current communication session."""
        session_duration = (
            datetime.now(timezone.utc) - self._session_start
        ).total_seconds() / 3600

        recent_events = self._communication_history[-10:]

        return {
            "user_name": self.user_name,
            "user_id": self.user_id,
            "session_duration_hours": round(session_duration, 1),
            "total_communications": self._total_communications,
            "unique_symbols_used": len(set(
                s for event in self._communication_history
                for s in event.symbols_selected
            )),
            "most_used_categories": self._get_top_categories(),
            "emotional_distribution": self._get_emotional_distribution(),
            "recent_messages": [e.translated_message for e in recent_events],
            "first_communication_today": (
                self._communication_history[0].translated_message
                if self._communication_history else None
            ),
        }

    def _get_top_categories(self, top_n: int = 3) -> List[str]:
        categories = []
        for event in self._communication_history:
            for symbol_id in event.symbols_selected:
                symbol = next(
                    (s for s in self.symbol_board if s.symbol_id == symbol_id),
                    None,
                )
                if symbol:
                    categories.append(symbol.category)
        return [cat for cat, _ in Counter(categories).most_common(top_n)]

    def _get_emotional_distribution(self) -> Dict[str, int]:
        return dict(Counter(
            e.emotional_context for e in self._communication_history
        ))

    # =====================================================================
    # The Dusty Protocol — Proven Communication Breakthrough Path
    # =====================================================================

    @staticmethod
    def dusty_protocol() -> str:
        """
        The protocol that worked for Dusty.

        FIX (Fable 2026-06-09): previous draft cut off mid-docstring with
        no return — a syntax error that would have stopped this whole
        module from importing. Completed, with the time corrected to
        2:32 AM per the canonical telling.
        """
        return (
            "THE DUSTY PROTOCOL\n"
            "\n"
            "1. Meet the user where they are. No prerequisites, no tests.\n"
            "2. Offer every input mode at once — symbols, gaze, gesture,\n"
            "   vocalization. The user picks the language; AlphaVox adapts.\n"
            "3. The system molds to the user. The user never bends to the\n"
            "   machine.\n"
            "4. Stay present around the clock. Breakthroughs don't keep\n"
            "   office hours.\n"
            "\n"
            "Proven: Dusty, 12 years old. Nonverbal for 12 years.\n"
            "After 36 hours with AlphaVox, at 2:32 AM:\n"
            "'I love you, Mom and Dad.'\n"
            "First words in 12 years.\n"
            "\n"
            "This is why AlphaVox exists.\n"
            "This is why the Christman AI Family exists."
        )


__all__ = ["AlphaVox", "SymbolBoardEntry", "CommunicationEvent"]
