import os

from .costs import cost


class RiskManager:
    def __init__(self, capital, max_positions, max_theme_positions, daily_loss_limit, stop_file="STOP"):
        self.capital = capital
        self.max_positions = max_positions
        self.max_theme_positions = max_theme_positions
        self.daily_loss_limit = daily_loss_limit
        self.stop_file = stop_file

    def trading_halted(self):
        return os.path.exists(self.stop_file)

    def daily_loss_limit_hit(self, equity, day_start_equity):
        return equity - day_start_equity <= -self.daily_loss_limit

    def max_positions_reached(self, open_positions):
        return len(open_positions) >= self.max_positions

    def theme_limit_reached(self, open_positions, src):
        if src == "core":
            return False
        return sum(p.get("src", "core") != "core" for p in open_positions.values()) >= self.max_theme_positions

    def position_size(self, cash, price):
        budget = min(cash, self.capital / self.max_positions)
        return int((budget - cost(budget, False)) // price)
