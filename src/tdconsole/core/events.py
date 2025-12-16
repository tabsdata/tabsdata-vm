# db/events.py
from sqlalchemy import event, inspect, update
from .models import Instance
from sqlalchemy.orm import object_session
from time import sleep


@event.listens_for(Instance, "after_update")
def manage_working_instance(mapper, connection, target):
    state = inspect(target)
    working_history = state.attrs.working.history

    if working_history.has_changes():
        old = working_history.deleted[0] if working_history.deleted else None
        new = working_history.added[0] if working_history.added else None

        if old is False and new is True:
            session = object_session(target)
            app = session.info.get("app")
            stmt = (
                update(Instance)
                .where(
                    Instance.name != target.name
                )  # exclude the one that was set to working
                .where(
                    Instance.working.is_(True)
                )  # optional: only touch rows that are currently True
                .values(working=False)
            )
            connection.execute(stmt)
            app.working_instance = target
            return

    if target.working is True:
        changed = [
            attr.key
            for attr in state.attrs
            if attr.key != "working" and attr.history.has_changes()
        ]
        if not changed:
            return
        session = object_session(target)
        app = session.info.get("app")
        app.working_instance = target
        return
