from pathlib import Path

from magboltz_gui.input_cards import InputCards


def load(filename: Path) -> InputCards:
    return InputCards()

def save (input_cards: InputCards, filename: Path) -> None:

    gas_ids = [gas.gas_id for gas in input_cards.gases] + [80] * (6 - len(input_cards.gases))
    gas_fracs = [gas.gas_frac for gas in input_cards.gases] + [0.] * (6 - len(input_cards.gases))

    with filename.open('w') as f:
        # Card 1
        f.write(f"{len(input_cards.gases)}\t{input_cards.number_of_real_collisions}\t{input_cards.final_energy}\n")

        # Card 2
        f.write("\t".join(str(v) for v in gas_ids)+"\n")

        # Card 3
        f.write("\t".join(str(v) for v in gas_fracs))
        f.write(f"\t{input_cards.gas_temperature}\t{input_cards.gas_pressure}\n")

        # Card 4
        f.write(f"{input_cards.electric_field}\t{input_cards.magnetic_field}\t{input_cards.angle}\n")
