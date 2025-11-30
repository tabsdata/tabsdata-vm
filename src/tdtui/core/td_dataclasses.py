from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional
import weakref


@dataclass
class FieldChange:
    """Represents a single change to a field on a TabsdataInstance."""

    instance: weakref.ReferenceType["TabsdataInstance"]
    attribute: str
    old: Any
    new: Any
    created_at: datetime
    handled: bool = False
    handled_at: Optional[datetime] = None

    def get_instance(self) -> Optional["TabsdataInstance"]:
        """Return the live instance, or None if it was garbage collected."""
        return self.instance()


@dataclass
class TabsdataInstance:
    name: str
    pid: Optional[str]
    status: str
    cfg_ext: Optional[str]
    cfg_int: Optional[str]
    arg_ext: Optional[str]
    arg_int: Optional[str]

    # internal change log
    _changes: List[FieldChange] = field(default_factory=list, init=False, repr=False)

    def __setattr__(self, key: str, value: Any) -> None:
        # Let private / internal attributes set normally with no tracking
        if key.startswith("_"):
            object.__setattr__(self, key, value)
            return

        # If the attribute already exists, track change
        if hasattr(self, key):
            old_value = getattr(self, key)
            if old_value != value:
                change = FieldChange(
                    instance=weakref.ref(self),
                    attribute=key,
                    old=old_value,
                    new=value,
                    created_at=datetime.now(),
                )
                # write directly to avoid going through __setattr__ again
                self._changes.append(change)

        # Actually set the attribute
        object.__setattr__(self, key, value)

    # ---- Helpers for working with changes ----

    @property
    def changes(self) -> List[FieldChange]:
        """All changes (handled and unhandled)."""
        return self._changes

    def pending_changes(self) -> List[FieldChange]:
        """Return all unhandled changes."""
        return [c for c in self._changes if not c.handled]

    def mark_change_handled(self, change: FieldChange) -> None:
        """Mark a specific change as handled."""
        change.handled = True
        change.handled_at = datetime.now()

    def mark_changes_handled(
        self,
        attribute: Optional[str] = None,
        only_latest: bool = False,
    ) -> None:
        """
        Mark changes as handled.

        - attribute=None  → all pending changes
        - attribute="port" → only changes for that attribute
        - only_latest=True → only the most recent matching change
        """
        pending = [c for c in self._changes if not c.handled]
        if attribute is not None:
            pending = [c for c in pending if c.attribute == attribute]

        if not pending:
            return

        if only_latest:
            pending = [pending[-1]]

        now = datetime.now()
        for c in pending:
            c.handled = True
            c.handled_at = now
