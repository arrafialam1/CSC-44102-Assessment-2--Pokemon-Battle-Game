# I acknowledge the use of Microsoft Copilot (M365 Copilot, Microsoft, https://copilot.microsoft.com/) to co-create code in this file.

import json
import os
import random
import tkinter as tk
from dataclasses import dataclass
from typing import List, Tuple, Optional

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
    burn: int = 0  # remaining turns of burn (0 = none)


# Small static roster (consistent across versions)
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
    return Pokemon(template.name, template.ptype, template.max_hp, template.max_hp, list(template.moves), 0)


def apply_burn(p: Pokemon) -> int:
    """Apply burn damage at start of turn. Returns damage dealt."""
    if p.burn > 0 and p.hp > 0:
        p.burn -= 1
        dmg = 2
        p.hp = clamp(p.hp - dmg, 0, p.max_hp)
        return dmg
    return 0


def deal_damage(attacker: Pokemon, defender: Pokemon, move: Move) -> dict:
    if random.randint(1, 100) > move.accuracy:
        return {"missed": True, "damage": 0, "crit": False, "mult": 1.0, "burned": False}

    base = move.power + random.randint(-2, 2)
    mult = type_multiplier(move.mtype, defender.ptype)
    crit = random.random() < 0.10
    if crit:
        base = int(base * 1.5)

    dmg = max(1, int(base * mult)) if move.power > 0 else 0
    defender.hp = clamp(defender.hp - dmg, 0, defender.max_hp)

    # Fire moves have 20% chance to burn
    burned = False
    if move.mtype == "Fire" and dmg > 0 and defender.hp > 0 and defender.burn == 0 and random.random() < 0.20:
        defender.burn = 3
        burned = True

    return {"missed": False, "damage": dmg, "crit": crit, "mult": mult, "burned": burned}


def choose_enemy_move(p: Pokemon) -> Move:
    weighted = [m for m in p.moves for _ in (range(2) if m.mtype != "Normal" else range(1))]
    return random.choice(weighted)


# ---------- Manual DB loader ----------
def load_manual_db(path: str) -> Optional[List[Pokemon]]:
    """Load Pokémon list from a simple JSON DB. Returns None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    mons_raw = data.get("pokemon") if isinstance(data, dict) else None
    if not isinstance(mons_raw, list) or not mons_raw:
        return None

    mons: List[Pokemon] = []
    for entry in mons_raw:
        try:
            name = str(entry.get("name", "Unknown"))
            ptype = str(entry.get("type", "Normal")).capitalize()
            hp = int(entry.get("hp", 60))
            moves_raw = entry.get("moves", [])
            mv_objs: List[Move] = []
            for mv in moves_raw:
                mv_name = str(mv.get("name", "Tackle"))
                mv_type = str(mv.get("type", "Normal")).capitalize()
                mv_power = int(mv.get("power", 10))
                mv_acc = int(mv.get("accuracy", 100))
                mv_objs.append(Move(mv_name, mv_type, mv_power, mv_acc))
            # Require at least 3 moves; pad with basic moves if needed
            while len(mv_objs) < 3:
                mv_objs.append(Move("Tackle", "Normal", 10, 100))
            mons.append(Pokemon(name=name, ptype=ptype, max_hp=hp, hp=hp, moves=mv_objs[:3]))
        except Exception:
            # Skip malformed entries
            continue

    return mons or None


def build_battle_entities_from_db(db_mons: List[Pokemon]) -> Tuple[List[Pokemon], Pokemon]:
    """Select a party of 2 and 1 enemy from DB mons."""
    if len(db_mons) < 3:
        raise ValueError("DB too small for battle")
    p1, p2, enemy = random.sample(db_mons, 3)
    party = [clone_pokemon(p1), clone_pokemon(p2)]
    return party, clone_pokemon(enemy)


# ---------- GUI ----------
class BattleApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Pokemon Battle - Manual DB (Best of 3)")
        root.resizable(False, False)

        # Match state
        self.player_wins = 0
        self.enemy_wins = 0
        self.round_num = 0

        # Manual DB load
        base = os.path.dirname(__file__)
        data_dir = os.path.abspath(os.path.join(base, "..", "data"))
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, "pokedex_min.json")
        self.db_mons = load_manual_db(db_path)
        self.used_db = self.db_mons is not None and isinstance(self.db_mons, list) and len(self.db_mons) >= 3

        source_pool = self.db_mons if self.used_db else ROSTER  # type: ignore[arg-type]
        p1, p2 = random.sample(source_pool, 2)
        self.party_templates: List[Pokemon] = [p1, p2]
        self.party: List[Pokemon] = [clone_pokemon(p1), clone_pokemon(p2)]
        self.active_idx = 0
        self.player: Pokemon = self.party[self.active_idx]
        # Placeholder enemy (re-chosen each round in start_new_round)
        self.enemy: Pokemon = clone_pokemon(random.choice(source_pool))
        self.potion_count = 2
        # Persistent record
        self.record = self.load_record()

        # Title & score
        self.lbl_title = tk.Label(root, text="", font=("Arial", 14, "bold"), fg="#2c3e50")
        self.lbl_title.pack(pady=10)
        self.lbl_score = tk.Label(root, text="", font=("Arial", 12, "italic"), fg="#34495e")
        self.lbl_score.pack(pady=(0, 6))
        # Record label
        self.lbl_record = tk.Label(root, text="", font=("Arial", 11), fg="#7f8c8d")
        self.lbl_record.pack(pady=(0, 6))

        # HP Display
        hp_frame = tk.Frame(root)
        hp_frame.pack(pady=5)

        self.lbl_player_hp = tk.Label(hp_frame, text=self.format_hp(self.player, "You"),
                                      font=("Courier", 11), fg="#e74c3c", anchor="w", width=40)
        self.lbl_player_hp.pack()

        self.lbl_enemy_hp = tk.Label(hp_frame, text=self.format_hp(self.enemy, "Foe"),
                                     font=("Courier", 11), fg="#3498db", anchor="w", width=40)
        self.lbl_enemy_hp.pack()

        # Battle log
        self.txt_log = tk.Text(root, height=10, width=50, wrap=tk.WORD, state=tk.DISABLED,
                               font=("Arial", 10), bg="#ecf0f1")
        self.txt_log.pack(pady=10, padx=10)

        # Move buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        self.move_buttons: List[tk.Button] = []
        for i, move in enumerate(self.player.moves):
            btn = tk.Button(btn_frame, text=f"{move.name}\n({move.mtype} {move.power})",
                            command=lambda idx=i: self.on_move_click(idx),
                            width=15, height=3, font=("Arial", 9))
            btn.grid(row=0, column=i, padx=5)
            self.move_buttons.append(btn)

        # Action buttons
        action_frame = tk.Frame(root)
        action_frame.pack(pady=5)

        self.btn_switch = tk.Button(action_frame, text="Switch Pokemon", command=self.on_switch,
                                    width=15, font=("Arial", 9), bg="#3498db", fg="white")
        self.btn_switch.grid(row=0, column=0, padx=5)

        self.btn_potion = tk.Button(action_frame, text=f"Potion (+15 HP) [{self.potion_count}]",
                                    command=self.on_potion,
                                    width=20, font=("Arial", 9), bg="#f39c12", fg="white")
        self.btn_potion.grid(row=0, column=1, padx=5)

        self.btn_restart = tk.Button(action_frame, text="New Match", command=self.restart,
                                     width=15, font=("Arial", 9), bg="#27ae60", fg="white")
        self.btn_restart.grid(row=0, column=2, padx=5)

        # Keyboard hotkeys
        root.bind("1", lambda e: self.on_move_click(0))
        root.bind("2", lambda e: self.on_move_click(1))
        root.bind("3", lambda e: self.on_move_click(2))
        root.bind("p", lambda e: self.on_potion())
        root.bind("P", lambda e: self.on_potion())
        root.bind("s", lambda e: self.on_switch())
        root.bind("S", lambda e: self.on_switch())
        root.bind("r", lambda e: self.restart())
        root.bind("R", lambda e: self.restart())

        self.update_record_label()
        # Start match
        self.restart()

    # ---------- Persistence ----------
    def record_path(self) -> str:
        base = os.path.dirname(__file__)
        data_dir = os.path.abspath(os.path.join(base, "..", "data"))
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

    def update_score_label(self) -> None:
        self.lbl_score.config(text=f"Score: You {self.player_wins} - {self.enemy_wins} Foe")

    def format_hp(self, pokemon: Pokemon, label: str) -> str:
        hp_percent = pokemon.hp / pokemon.max_hp if pokemon.max_hp > 0 else 0
        bar_length = 20
        filled = int(bar_length * hp_percent)
        bar = "█" * filled + "░" * (bar_length - filled)
        burn_status = " (BRN)" if pokemon.burn > 0 else ""
        return f"{label}: {pokemon.name:<10} [{pokemon.ptype}] {bar} {pokemon.hp}/{pokemon.max_hp} HP{burn_status}"

    def log_message(self, message: str) -> None:
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def start_new_round(self) -> None:
        # Increment round
        self.round_num += 1
        # Reset party & enemy
        self.party = [clone_pokemon(t) for t in self.party_templates]
        self.active_idx = 0
        self.player = self.party[self.active_idx]
        # Reset potions
        self.potion_count = 2
        self.btn_potion.config(text=f"Potion (+15 HP) [{self.potion_count}]", state=tk.NORMAL)
        # Enemy selection
        pool = self.db_mons if self.used_db and self.db_mons else ROSTER
        enemy_candidates = [m for m in pool if m.name not in {t.name for t in self.party_templates}] or pool
        self.enemy = clone_pokemon(random.choice(enemy_candidates))
        db_note = " [DB]" if self.used_db else ""
        self.lbl_title.config(text=f"Round {self.round_num} - A wild {self.enemy.name} appeared!{db_note}")
        self.update_score_label()
        # Update move buttons
        for i, mv in enumerate(self.player.moves):
            if i < len(self.move_buttons):
                self.move_buttons[i].config(text=f"{mv.name}\n({mv.mtype} {mv.power})",
                                            command=lambda idx=i: self.on_move_click(idx))
        # Clear log
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.delete(1.0, tk.END)
        self.txt_log.config(state=tk.DISABLED)
        self.update_display()
        self.open_choice_dialog()
        self.log_message("Battle started! Choose your move...")
        self.log_message("Hotkeys: 1-3 (moves), P (potion), S (switch), R (restart)")
        self.enable_moves()

    def update_display(self) -> None:
        self.lbl_player_hp.config(text=self.format_hp(self.player, "You"))
        self.lbl_enemy_hp.config(text=self.format_hp(self.enemy, "Foe"))

    def disable_moves(self) -> None:
        for btn in self.move_buttons:
            btn.config(state=tk.DISABLED)
        self.btn_switch.config(state=tk.DISABLED)
        self.btn_potion.config(state=tk.DISABLED)

    def enable_moves(self) -> None:
        for btn in self.move_buttons:
            btn.config(state=tk.NORMAL)
        self.btn_switch.config(state=tk.NORMAL)
        if self.potion_count > 0:
            self.btn_potion.config(state=tk.NORMAL)

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

    def on_switch(self) -> None:
        """Allow player to switch to another Pokemon in their party."""
        if self.player.hp <= 0 or self.enemy.hp <= 0:
            return

        # Find available Pokemon to switch to
        options = [(i, p) for i, p in enumerate(self.party) if i != self.active_idx and p.hp > 0]
        if not options:
            self.log_message("No available Pokemon to switch to!")
            return

        # Create switch dialog
        switch_win = tk.Toplevel(self.root)
        switch_win.title("Switch Pokemon")
        switch_win.geometry("300x150")

        tk.Label(switch_win, text="Choose a Pokemon:", font=("Arial", 11, "bold")).pack(pady=10)

        def do_switch(idx: int) -> None:
            switch_win.destroy()
            self.active_idx = idx
            self.player = self.party[self.active_idx]
            self.log_message(f"You switched to {self.player.name}!")
            self.update_display()
            # Update move buttons for new Pokemon
            for i, move in enumerate(self.player.moves):
                if i < len(self.move_buttons):
                    self.move_buttons[i].config(
                        text=f"{move.name}\n({move.mtype} {move.power})",
                        command=lambda idx=i: self.on_move_click(idx)
                    )
            self.root.after(600, self.enemy_turn)

        for idx, poke in options:
            btn_text = f"{poke.name} ({poke.hp}/{poke.max_hp} HP)"
            tk.Button(switch_win, text=btn_text, width=20, command=lambda i=idx: do_switch(i)).pack(pady=5)

    def on_potion(self) -> None:
        """Use a potion to heal the active Pokemon."""
        if self.player.hp <= 0 or self.enemy.hp <= 0:
            return

        if self.potion_count <= 0:
            self.log_message("No potions left!")
            return

        self.disable_moves()

        old_hp = self.player.hp
        self.player.hp = clamp(self.player.hp + 15, 0, self.player.max_hp)
        healed = self.player.hp - old_hp

        self.potion_count -= 1
        self.btn_potion.config(text=f"Potion (+15 HP) [{self.potion_count}]")

        self.log_message(f"You used a Potion! {self.player.name} healed {healed} HP.")
        self.update_display()

        if self.potion_count <= 0:
            self.btn_potion.config(state=tk.DISABLED)

        # Enemy turn after using potion
        self.root.after(600, self.enemy_turn)

    def on_move_click(self, move_idx: int) -> None:
        if self.player.hp <= 0 or self.enemy.hp <= 0:
            return
        self.disable_moves()
        burn_dmg = apply_burn(self.player)
        if burn_dmg > 0:
            self.log_message(f"{self.player.name} is hurt by burn (-{burn_dmg}).")
            self.update_display()
            if self.player.hp <= 0 and self._end_round_if_needed():
                return
        move = self.player.moves[move_idx]
        result = deal_damage(self.player, self.enemy, move)
        msg = self.describe_result(self.player, move, result, self.enemy.name)
        if result.get("burned"):
            msg += f" {self.enemy.name} was burned!"
        self.log_message(msg)
        self.update_display()
        if self._end_round_if_needed():
            return
        self.root.after(700, self.enemy_turn)

    def enemy_turn(self) -> None:
        if self.enemy.hp <= 0 or self.player.hp <= 0:
            if self._end_round_if_needed():
                return
        burn_dmg = apply_burn(self.enemy)
        if burn_dmg > 0:
            self.log_message(f"{self.enemy.name} is hurt by burn (-{burn_dmg}).")
            self.update_display()
            if self._end_round_if_needed():
                return
        move = choose_enemy_move(self.enemy)
        result = deal_damage(self.enemy, self.player, move)
        msg = self.describe_result(self.enemy, move, result, self.player.name)
        if result.get("burned"):
            msg += f" {self.player.name} was burned!"
        self.log_message(msg)
        self.update_display()
        if self._end_round_if_needed():
            return
        self.enable_moves()

    def restart(self) -> None:
        # Reset match
        self.player_wins = 0
        self.enemy_wins = 0
        self.round_num = 0
        self.start_new_round()

    def _end_round_if_needed(self) -> bool:
        all_party_fainted = all(p.hp <= 0 for p in self.party)
        enemy_fainted = self.enemy.hp <= 0
        if enemy_fainted and all_party_fainted:
            self.log_message("\n🤝 Both sides fainted! Round is a tie! 🤝")
            self._end_round(None)
            return True
        elif enemy_fainted:
            self.log_message(f"\n🎉 {self.enemy.name} fainted! You win the round! 🎉")
            self._end_round(True)
            return True
        elif all_party_fainted:
            self.log_message("\n💀 All your Pokémon fainted! You lose the round! 💀")
            self._end_round(False)
            return True
        return False

    def _end_round(self, player_won: bool | None) -> None:
        if player_won is True:
            self.player_wins += 1
        elif player_won is False:
            self.enemy_wins += 1
        self.update_score_label()
        self.disable_moves()
        if self.player_wins >= 2:
            self.log_message("\n🏆 You won the match! Congratulations! 🏆")
            self.record['wins'] += 1
            self.save_record()
            self.update_record_label()
            return
        if self.enemy_wins >= 2:
            self.log_message("\n💔 You lost the match! Better luck next time. 💔")
            self.record['losses'] += 1
            self.save_record()
            self.update_record_label()
            return
        self.log_message("Prepare for the next round...")
        self.root.after(1800, self.start_new_round)

    def open_choice_dialog(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("Choose Your Lead Pokémon")
        win.grab_set()
        tk.Label(win, text="Choose your opening Pokémon:", font=("Arial", 12, "bold")).pack(pady=8)
        frame = tk.Frame(win)
        frame.pack(padx=10, pady=10)
        def choose(idx: int) -> None:
            self.active_idx = idx
            self.player = self.party[self.active_idx]
            for i, mv in enumerate(self.player.moves):
                if i < len(self.move_buttons):
                    self.move_buttons[i].config(text=f"{mv.name}\n({mv.mtype} {mv.power})",
                                                command=lambda idx=i: self.on_move_click(idx))
            db_note = " [DB]" if self.used_db else ""
            self.lbl_title.config(text=f"A wild {self.enemy.name} appeared! Go {self.player.name}!{db_note}")
            self.update_display()
            win.destroy()
        for i, mon in enumerate(self.party):
            txt = f"{mon.name} [{mon.ptype}]\nHP {mon.max_hp}"
            tk.Button(frame, text=txt, width=20, height=4, command=lambda i=i: choose(i)).grid(row=0, column=i, padx=6)
        self.enable_moves()


def main() -> None:
    root = tk.Tk()
    BattleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()