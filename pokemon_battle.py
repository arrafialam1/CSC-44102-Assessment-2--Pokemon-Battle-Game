# I acknowledge the use of Microsoft Copilot (M365 Copilot, Microsoft, https://copilot.microsoft.com/) to co-create code in this file.

import random
import tkinter as tk
import json
import os
from dataclasses import dataclass
from typing import List, Tuple

# ---------- Data (no dependencies) ----------

@dataclass
class Move:
    name: str
    mtype: str
    power: int
    accuracy: int = 100  # default to always hit unless specified

@dataclass
class Pokemon:
    name: str
    ptype: str
    max_hp: int
    hp: int
    moves: List[Move]

# Small static roster (consistent across both versions)
ROSTER = [
    Pokemon("Charmander", "Fire", 60, 60, [Move("Scratch", "Normal", 10), Move("Ember", "Fire", 14, 95), Move("Growl", "Normal", 6)]),
    Pokemon("Squirtle",   "Water", 62, 62, [Move("Tackle",  "Normal", 10), Move("Water Gun", "Water", 14, 95), Move("Tail Whip", "Normal", 6)]),
    Pokemon("Bulbasaur",  "Grass", 58, 58, [Move("Pound",   "Normal", 10), Move("Vine Whip", "Grass", 14, 95), Move("Growl", "Normal", 6)]),
]

# ---------- Type effectiveness (simple) ----------
EFFECT = {
    ("Fire", "Grass"): 2.0, ("Grass", "Water"): 2.0, ("Water", "Fire"): 2.0,
    ("Grass", "Fire"): 0.5, ("Water", "Grass"): 0.5, ("Fire", "Water"): 0.5,
}

def type_multiplier(att_type: str, def_type: str) -> float:
    return EFFECT.get((att_type, def_type), 1.0)

# ---------- Mechanics ----------
def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))

def clone_pokemon(template: Pokemon) -> Pokemon:
    return Pokemon(template.name, template.ptype, template.max_hp, template.max_hp, list(template.moves))

def deal_damage(attacker: Pokemon, defender: Pokemon, move: Move) -> dict:
    if random.randint(1, 100) > move.accuracy:
        return {"missed": True, "damage": 0, "crit": False, "mult": 1.0}

    base = move.power + random.randint(-2, 2)
    mult = type_multiplier(move.mtype, defender.ptype)
    crit = random.random() < 0.10
    if crit:
        base = int(base * 1.5)

    dmg = max(1, int(base * mult)) if move.power > 0 else 0
    defender.hp = clamp(defender.hp - dmg, 0, defender.max_hp)

    return {"missed": False, "damage": dmg, "crit": crit, "mult": mult}

def choose_enemy_move(p: Pokemon) -> Move:
    weighted = [m for m in p.moves for _ in (range(2) if m.mtype != "Normal" else range(1))]
    return random.choice(weighted)

# ---------- GUI ----------
class BattleApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Pokemon Battle - Best of 3")
        root.resizable(False, False)

        # Match state
        self.player_wins = 0
        self.enemy_wins = 0
        self.round_num = 0
        self.player_template = None  # chosen Pokemon template for the match

        # Persistent record
        self.record = self.load_record()

        # Title and Score
        self.lbl_title = tk.Label(root, text="", font=("Arial", 14, "bold"), fg="#2c3e50")
        self.lbl_title.pack(pady=(10, 0))
        
        self.lbl_score = tk.Label(root, text="", font=("Arial", 12, "italic"), fg="#34495e")
        self.lbl_score.pack(pady=(0, 10))

        # Record label
        self.lbl_record = tk.Label(root, text="", font=("Arial", 11), fg="#7f8c8d")
        self.lbl_record.pack(pady=(0, 6))

        # HP Display
        hp_frame = tk.Frame(root)
        hp_frame.pack(pady=5)
        
        self.lbl_player_hp = tk.Label(hp_frame, text="", font=("Courier", 11), fg="#e74c3c", anchor="w", width=40)
        self.lbl_player_hp.pack()
        
        self.lbl_enemy_hp = tk.Label(hp_frame, text="", font=("Courier", 11), fg="#3498db", anchor="w", width=40)
        self.lbl_enemy_hp.pack()

        # Battle log
        self.txt_log = tk.Text(root, height=10, width=50, wrap=tk.WORD, state=tk.DISABLED,
                               font=("Arial", 10), bg="#ecf0f1")
        self.txt_log.pack(pady=10, padx=10)

        # Move buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        
        self.move_buttons: List[tk.Button] = []
        # Create buttons once, we'll update them
        for i in range(len(ROSTER[0].moves)):
            btn = tk.Button(btn_frame, text="", command=lambda idx=i: self.on_move_click(idx),
                          width=15, height=3, font=("Arial", 9))
            btn.grid(row=0, column=i, padx=5)
            self.move_buttons.append(btn)

        # Restart button
        self.btn_restart = tk.Button(root, text="New Match", command=self.restart,
                                     width=20, font=("Arial", 10, "bold"), bg="#27ae60", fg="white")
        self.btn_restart.pack(pady=10)

        self.update_record_label()
        self.restart()

    # ---------- Persistence ----------
    def record_path(self) -> str:
        base = os.path.dirname(__file__)
        data_dir = os.path.join(base, "..", "data")
        data_dir = os.path.abspath(data_dir)
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "record.json")

    def load_record(self) -> dict:
        try:
            with open(self.record_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {"wins": int(data.get("wins", 0)), "losses": int(data.get("losses", 0)), "ties": int(data.get("ties", 0))}
        except Exception:
            pass
        return {"wins": 0, "losses": 0, "ties": 0}

    def save_record(self) -> None:
        try:
            with open(self.record_path(), "w", encoding="utf-8") as f:
                json.dump(self.record, f)
        except Exception:
            pass

    def update_record_label(self) -> None:
        self.lbl_record.config(text=f"Record: {self.record['wins']}W/{self.record['losses']}L/{self.record['ties']}T")

    def start_new_round(self) -> None:
        self.round_num += 1
        
        # Use chosen template for the whole match
        player_template = self.player_template or random.choice(ROSTER)
        # Enemy should not be the same species if possible
        enemy_candidates = [m for m in ROSTER if m.name != player_template.name] or ROSTER
        enemy_template = random.choice(enemy_candidates)

        self.player: Pokemon = clone_pokemon(player_template)
        self.enemy: Pokemon = clone_pokemon(enemy_template)

        self.lbl_title.config(text=f"Round {self.round_num} - A wild {self.enemy.name} appeared!")
        self.update_score_display()
        
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.delete(1.0, tk.END)
        self.txt_log.config(state=tk.DISABLED)
        
        self.log_message(f"Go {self.player.name}! Choose your move...")
        self.update_move_buttons()
        self.update_display()
        self.enable_moves()

    def open_choice_dialog(self) -> None:
        """Prompt player to choose a Pokémon before the match starts."""
        win = tk.Toplevel(self.root)
        win.title("Choose Your Pokémon")
        win.grab_set()
        tk.Label(win, text="Choose your Pokémon:", font=("Arial", 12, "bold")).pack(pady=8)

        frame = tk.Frame(win)
        frame.pack(padx=10, pady=10)

        def choose(mon: Pokemon) -> None:
            self.player_template = mon
            win.destroy()
            self.start_new_round()

        for i, mon in enumerate(ROSTER):
            moves = ", ".join(m.name for m in mon.moves)
            text = f"{mon.name} [{mon.ptype}]\nHP {mon.max_hp}\nMoves: {moves}"
            btn = tk.Button(frame, text=text, width=22, height=4, command=lambda m=mon: choose(m))
            btn.grid(row=0, column=i, padx=6)

    def format_hp(self, pokemon: Pokemon, label: str) -> str:
        hp_percent = pokemon.hp / pokemon.max_hp if pokemon.max_hp > 0 else 0
        bar_length = 20
        filled = int(bar_length * hp_percent)
        bar = "█" * filled + "░" * (bar_length - filled)
        return f"{label}: {pokemon.name:<10} [{pokemon.ptype}] {bar} {pokemon.hp}/{pokemon.max_hp} HP"

    def log_message(self, message: str) -> None:
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def update_display(self) -> None:
        self.lbl_player_hp.config(text=self.format_hp(self.player, "You"))
        self.lbl_enemy_hp.config(text=self.format_hp(self.enemy, "Foe"))

    def update_score_display(self) -> None:
        self.lbl_score.config(text=f"Score: You {self.player_wins} - {self.enemy_wins} Foe")

    def update_move_buttons(self) -> None:
        for i, move in enumerate(self.player.moves):
            btn = self.move_buttons[i]
            btn.config(text=f"{move.name}\n({move.mtype} {move.power})",
                       command=lambda idx=i: self.on_move_click(idx))

    def disable_moves(self) -> None:
        for btn in self.move_buttons:
            btn.config(state=tk.DISABLED)

    def enable_moves(self) -> None:
        for btn in self.move_buttons:
            btn.config(state=tk.NORMAL)

    def describe_result(self, attacker: Pokemon, move: Move, result: dict, target: str) -> str:
        if result["missed"]:
            return f"{attacker.name} used {move.name}, but it missed!"
        
        parts = []
        if result["crit"]:
            parts.append("Critical hit!")
        if result["mult"] > 1.0:
            parts.append("Super effective!")
        elif 0 < result["mult"] < 1.0:
            parts.append("Not very effective...")
        
        extra = " " + " ".join(parts) if parts else ""
        return f"{attacker.name} used {move.name}! Dealt {result['damage']} damage to {target}.{extra}"

    def on_move_click(self, move_idx: int) -> None:
        if self.player.hp <= 0 or self.enemy.hp <= 0:
            return

        self.disable_moves()

        # Player turn
        move = self.player.moves[move_idx]
        result = deal_damage(self.player, self.enemy, move)
        msg = self.describe_result(self.player, move, result, self.enemy.name)
        self.log_message(msg)
        self.update_display()

        if self.enemy.hp <= 0:
            self.handle_round_end(player_won=True)
            return

        # Enemy turn (delayed for readability)
        self.root.after(800, self.enemy_turn)

    def enemy_turn(self) -> None:
        if self.enemy.hp <= 0 or self.player.hp <= 0:
            return

        move = choose_enemy_move(self.enemy)
        result = deal_damage(self.enemy, self.player, move)
        msg = self.describe_result(self.enemy, move, result, self.player.name)
        self.log_message(msg)
        self.update_display()

        if self.player.hp <= 0:
            self.handle_round_end(player_won=False)
            return

        self.enable_moves()

    def handle_round_end(self, player_won: bool) -> None:
        if player_won:
            self.player_wins += 1
            self.log_message(f"\n🎉 {self.enemy.name} fainted! You win this round! 🎉")
        else:
            self.enemy_wins += 1
            self.log_message(f"\n💀 {self.player.name} fainted! You lost this round! 💀")
        
        self.update_score_display()

        if self.player_wins >= 2:
            self.log_message("\n🏆 You won the match! Congratulations! 🏆")
            self.disable_moves()
            self.record["wins"] += 1
            self.save_record()
            self.update_record_label()
        elif self.enemy_wins >= 2:
            self.log_message("\n💔 You lost the match! Better luck next time. 💔")
            self.disable_moves()
            self.record["losses"] += 1
            self.save_record()
            self.update_record_label()
        else:
            # Start next round after a delay
            self.log_message("Prepare for the next round...")
            self.root.after(2000, self.start_new_round)

    def restart(self) -> None:
        self.player_wins = 0
        self.enemy_wins = 0
        self.round_num = 0
        # Ask the user to choose their Pokémon at the start of each match
        self.open_choice_dialog()


def main() -> None:
    root = tk.Tk()
    BattleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
