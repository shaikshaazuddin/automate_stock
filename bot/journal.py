import datetime as dt
import json


class JsonlJournal:
    """Append one event to the journal. review.py learns from this file."""

    def __init__(self, path, mode, tz):
        self.path, self.mode, self.tz = path, mode, tz

    def record(self, **e):
        e["ts"] = dt.datetime.now(self.tz).isoformat(timespec="seconds")
        e["mode"] = self.mode
        with open(self.path, "a") as f:
            f.write(json.dumps(e) + "\n")
