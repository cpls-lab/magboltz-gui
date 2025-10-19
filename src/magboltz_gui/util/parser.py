from pathlib import Path

from magboltz_gui.data.input_cards import InputCards, InputGas


def load(filename: Path) -> InputCards:
    with filename.open("r") as f:
        # Card 1
        line = f.readline()
        parts = line.strip().split()
        num_gases = int(parts[0])
        number_of_real_collisions = int(parts[1])
        enable_penning = bool(parts[2] == "1")
        enable_thermal = bool(parts[3] == "1")
        final_energy = float(parts[4])

        # Card 2
        line = f.readline()
        gas_ids = [int(x) for x in line.strip().split()[:num_gases]]

        # Card 3
        line = f.readline()
        parts = line.strip().split()
        gas_fracs = [float(x) for x in parts[:num_gases]]
        gas_temperature = float(parts[6])
        gas_pressure = float(parts[7])

        # Card 4
        line = f.readline()
        parts = line.strip().split()
        electric_field = float(parts[0])
        magnetic_field = float(parts[1])
        angle = float(parts[2])

    # Rebuild gases list
    gases = [InputGas(gas_id=gas_ids[i], gas_frac=gas_fracs[i]) for i in range(num_gases)]

    return InputCards(
        gases=gases,
        number_of_real_collisions=number_of_real_collisions,
        enable_penning=enable_penning,
        enable_thermal=enable_thermal,
        final_energy=final_energy,
        gas_temperature=gas_temperature,
        gas_pressure=gas_pressure,
        electric_field=electric_field,
        magnetic_field=magnetic_field,
        angle=angle,
    )


def save(input_cards: InputCards, filename: Path) -> None:

    gas_ids = [gas.gas_id for gas in input_cards.gases] + [80] * (6 - len(input_cards.gases))
    gas_fracs = [gas.gas_frac for gas in input_cards.gases] + [0.0] * (6 - len(input_cards.gases))

    with filename.open("w") as f:
        # Card 1
        f.write(
            f"{len(input_cards.gases)}\t{input_cards.number_of_real_collisions}\t{'1' if input_cards.enable_penning else '0'}\t{'1' if input_cards.enable_thermal else '0'}\t{input_cards.final_energy}\n"
        )

        # Card 2
        f.write("\t".join(str(v) for v in gas_ids) + "\n")

        # Card 3
        f.write("\t".join(str(v) for v in gas_fracs))
        f.write(f"\t{input_cards.gas_temperature}\t{input_cards.gas_pressure}\n")

        # Card 4
        f.write(f"{input_cards.electric_field}\t{input_cards.magnetic_field}\t{input_cards.angle}\n")

        # Card 4N + 1
        f.write("{} {} {} {} {}\n".format(0, 0, 0, 0, 0.0))
