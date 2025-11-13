# CSC-44102 Assessment 2: Pokemon Game

## Overview
This is a Python-based Pokemon battle game created for CSC-44102 Assessment 2. The game allows players to choose a Pokemon and battle against computer-controlled opponents in a turn-based combat system.

## Features
- **Pokemon Selection**: Choose from Charmander (Fire), Squirtle (Water), or Bulbasaur (Grass)
- **Turn-based Combat**: Strategic battle system with multiple moves per Pokemon
- **Type Effectiveness**: Rock-paper-scissors style type advantages (Fire > Grass > Water > Fire)
- **Battle Statistics**: Track your wins, losses, and ties across game sessions
- **Move Variety**: Each Pokemon has unique moves with different power levels and accuracy
- **Critical Hits**: Random chance for extra damage
- **Recoil Damage**: High-power moves can cause recoil damage to the attacker
- **Dual Interfaces**: Play with CLI or GUI (tkinter) interface
- **Expandable Roster**: 12 Pokemon available in the data file

## How to Play
1. Run the game: `python3 pokemon_battle.py`
2. Choose your Pokemon from the available roster
3. Select moves during battle to defeat your opponent
4. Continue playing to improve your win/loss record
5. Watch the battle log and HP bars to track progress
6. Use the move buttons to attack during your turn

## Game Mechanics
- Each Pokemon has a type (Fire, Water, Grass) that determines type advantages
- Moves have different power levels and accuracy rates
- Type-effective moves deal 2x damage, while resisted moves deal 0.5x damage
- 10% chance of critical hits (1.5x damage multiplier)
- High-power moves (14+ power) have a 15% chance to cause 20% recoil damage

## AI Acknowledgment
This project was developed with the assistance of Microsoft Copilot (M365 Copilot) for code generation and game design, as permitted by the assessment guidelines.

## Author
Ar Rafi Alam Chowdhury (y5q86@students.keele.ac.uk)
