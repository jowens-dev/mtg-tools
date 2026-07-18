sample_line = "4x Lightning Bolt"

print("--- STEP 1: Raw Data ---")
print(f"Input: '{sample_line}'")

parts = sample_line.split(" ", 1) 

print("\n--- STEP 2: Splitting ---")
print(f"Result: {parts}")

raw_qty = parts[0]
raw_name = parts[1]

clean_qty = raw_qty.replace('x', '').strip()
clean_name = raw_name.strip()

print("\n--- STEP 3: Cleaning ---")
print(f"Quantity: {clean_qty}")
print(f"Card Name: {clean_name}")

def parse_single_line(line: str) -> dict:
    try:
        parts = line.split(" ", 1)
        qty = int(parts[0].replace('x', '').strip())
        name = parts[1].strip()
        return {"quantity": qty, "name": name}
    except ValueError:
        return {"quantity": 1, "name": line.strip()}

print("\n--- STEP 4: Testing the Function ---")
print(parse_single_line("10 Snow-Covered Island"))
print(parse_single_line("Ragavan, Nimble Pilferer"))
