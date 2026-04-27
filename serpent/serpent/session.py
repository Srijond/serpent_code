"""Session persistence for chat history."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from serpent.config import SerpentConfig


class SessionEvent(BaseModel):
    """A single event in the session."""
    timestamp: datetime
    role: str
    content: str
    metadata: dict = {}


class ChatSession(BaseModel):
    """A persisted chat session."""
    id: str
    created_at: datetime
    updated_at: datetime
    provider: str
    model: str
    working_dir: str
    events: list[SessionEvent] = []
    summary: Optional[str] = None


class SessionStore:
    """Manages persistent session storage."""
    
    def __init__(self, config: SerpentConfig) -> None:
        self.config = config
        self.session_dir = config.session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._current_session: Optional[ChatSession] = None
    
    def create_session(self, provider: str, model: str) -> ChatSession:
        """Create a new session."""
        session = ChatSession(
            id=str(uuid.uuid4())[:8],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            provider=provider,
            model=model,
            working_dir=str(self.config.working_dir),
        )
        self._current_session = session
        self._save_session(session)
        return session
    
    def load_session(self, session_id: str) -> Optional[ChatSession]:
        """Load a session by ID."""
        path = self.session_dir / f"{session_id}.json"
        if not path.exists():
            return None
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        session = ChatSession.model_validate(data)
        self._current_session = session
        return session
    
    def list_sessions(self) -> list[ChatSession]:
        """List all saved sessions."""
        sessions = []
        for path in self.session_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append(ChatSession.model_validate(data))
            except Exception:
                continue
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)
    
    def add_event(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        """Add an event to the current session."""
        if not self._current_session:
            return
        
        event = SessionEvent(
            timestamp=datetime.now(),
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self._current_session.events.append(event)
        self._current_session.updated_at = datetime.now()
        self._save_session(self._current_session)
    
    def get_current_session(self) -> Optional[ChatSession]:
        """Get the current active session."""
        return self._current_session
    
    def compact_session(self, summary: str) -> None:
        """Replace old events with a summary."""
        if not self._current_session:
            return
        
        self._current_session.summary = summary
        recent_events = self._current_session.events[-4:] if len(self._current_session.events) > 4 else self._current_session.events
        self._current_session.events = recent_events
        self._save_session(self._current_session)
    
    def _save_session(self, session: ChatSession) -> None:
        """Save session to disk."""
        path = self.session_dir / f"{session.id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session.model_dump(mode="json"), f, indent=2, default=str)