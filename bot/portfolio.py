import json
import os


class JsonPortfolioStore:
    def __init__(self, path, capital):
        self.path, self.capital = path, capital

    def load(self):
        if os.path.exists(self.path):
            return json.load(open(self.path))
        return {"cash": self.capital, "pos": {}, "day": "", "day_start": self.capital, "log": []}

    def save(self, state):
        json.dump(state, open(self.path, "w"), indent=2)
