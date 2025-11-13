# I acknowledge the use of Microsoft Copilot (M365 Copilot, Microsoft, https://copilot.microsoft.com/) to co-create code in this file.

import random
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
        return {"missed": True, "damage": 0, "crit": False, "mult": 1.0, "recoil": 0}

    base = move.power + random.randint(-2, 2)
    mult = type_multiplier(move.mtype, defender.ptype)
    crit = random.random() < 0.10
    if crit:
        base = int(base * 1.5)

    dmg = max(1, int(base * mult)) if move.power > 0 else 0
    defender.hp = clamp(defender.hp - dmg, 0, defender.max_hp)

    # Recoil mechanic: high-power moves (≥14) have 15% chance of 20% recoil
    recoil = 0
    if move.power >= 14 and dmg > 0 and random.random() < 0.15:
        recoil = max(1, int(dmg * 0.20))
        attacker.hp = clamp(attacker.hp - recoil, 0, attacker.max_hp)

    return {"missed": False, "damage": dmg, "crit": crit, "mult": mult, "recoil": recoil}

def choose_enemy_move(p: Pokemon) -> Move:
    weighted = [m for m in p.moves for _ in (range(2) if m.mtype != "Normal" else range(1))]
    return random.choice(weighted)

# ---------- CLI ----------
def describe_damage(origin: Pokemon, move: Move, report: dict, target_label: str) -> None:
    if report["missed"]:
        print(f"{origin.name} used {move.name}, but it missed {target_label}!")
        return

    parts: List[str] = []
    if report["crit"]:
        parts.append("critical hit")
    if report["mult"] > 1.0:
        parts.append("super effective")
    if 0 < report["mult"] < 1.0:
        parts.append("not very effective")
    extra = f" ({', '.join(parts)})" if parts else ""
    print(f"{origin.name} used {move.name}! It dealt {report['damage']} damage{extra} to {target_label}.")
    
    if report.get("recoil", 0) > 0:
        print(f"  {origin.name} took {report['recoil']} recoil damage!")


def print_status(player: Pokemon, enemy: Pokemon) -> None:
    print()
    print(f"You:   {player.name:<10} [{player.ptype}] {player.hp}/{player.max_hp} HP")
    print(f"Foe:   {enemy.name:<10} [{enemy.ptype}] {enemy.hp}/{enemy.max_hp} HP")


def prompt_pokemon_choice() -> Pokemon:
    print("Choose your Pokémon:")
    for idx, mon in enumerate(ROSTER, start=1):
        moves = ", ".join(move.name for move in mon.moves)
        print(f" {idx}. {mon.name:<10} [{mon.ptype}] HP {mon.max_hp} | Moves: {moves}")

    while True:
        choice = input("> ").strip()
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(ROSTER):
                return ROSTER[index]
        print("Invalid choice. Enter the number of the Pokémon you want to use.")


def prompt_move(player: Pokemon) -> Move:
    while True:
        print("Choose your move:")
        for idx, move in enumerate(player.moves, start=1):
            print(f" {idx}. {move.name} ({move.mtype}, power {move.power}, acc {move.accuracy}%)")
        choice = input("> ").strip()
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(player.moves):
                return player.moves[index]
        print("Invalid choice. Please enter the number of the move you want to use.")


def player_turn(player: Pokemon, enemy: Pokemon) -> bool:
    move = prompt_move(player)
    result = deal_damage(player, enemy, move)
    describe_damage(player, move, result, f"the wild {enemy.name}")
    return enemy.hp <= 0


def enemy_turn(player: Pokemon, enemy: Pokemon) -> bool:
    move = choose_enemy_move(enemy)
    result = deal_damage(enemy, player, move)
    describe_damage(enemy, move, result, player.name)
    return player.hp <= 0


def battle(player: Pokemon, enemy: Pokemon) -> str:
    print(f"A wild {enemy.name} appeared!")
    print(f"Go! {player.name}!")

    while player.hp > 0 and enemy.hp > 0:
        print_status(player, enemy)
        if player_turn(player, enemy):
            break
        if enemy.hp <= 0:
            break
        if enemy_turn(player, enemy):
            break

    if player.hp <= 0 and enemy.hp <= 0:
        print("Both Pokémon fainted. It's a tie!")
        return "tie"
    if enemy.hp <= 0:
        print(f"The wild {enemy.name} fainted. You win!")
        return "win"

    print(f"{player.name} fainted. You lost!")
    return "loss"


def create_combatants() -> Tuple[Pokemon, Pokemon]:
    player_template = prompt_pokemon_choice()
    enemy_pool = [mon for mon in ROSTER if mon is not player_template]
    enemy_template = random.choice(enemy_pool or ROSTER)
    return clone_pokemon(player_template), clone_pokemon(enemy_template)


def main() -> None:
    # Load persistent record (stored next to data/pokedex_min.json)
    def record_path() -> str:
        base = os.path.dirname(__file__)
        data_dir = os.path.join(base, "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "record.json")

    def load_record() -> dict:
        try:
            with open(record_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {"wins": int(data.get("wins", 0)), "losses": int(data.get("losses", 0)), "ties": int(data.get("ties", 0))}
        except Exception:
            pass
        return {"wins": 0, "losses": 0, "ties": 0}

    def save_record(rec: dict) -> None:
        try:
            with open(record_path(), "w", encoding="utf-8") as f:
                json.dump(rec, f)
        except Exception:
            # Non-fatal: just continue without crashing the game
            pass

    rec = load_record()
    wins, losses, ties = rec["wins"], rec["losses"], rec["ties"]

    while True:
        player, enemy = create_combatants()
        outcome = battle(player, enemy)

        if outcome == "win":
            wins += 1
        elif outcome == "loss":
            losses += 1
        else:
            ties += 1

        # Persist record after each battle
        rec = {"wins": wins, "losses": losses, "ties": ties}
        save_record(rec)

        print(f"Record: {wins} win(s), {losses} loss(es), {ties} tie(s)")

        again = input("Play again? (y/n): ").strip().lower()
        if again not in {"y", "yes"}:
            print("Thanks for playing!")
            # Save on exit as well
            save_record({"wins": wins, "losses": losses, "ties": ties})
            break


if __name__ == "__main__":
    main()