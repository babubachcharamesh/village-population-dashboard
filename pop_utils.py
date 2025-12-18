def get_marriage_to_village_id(village_id: int, counter: int) -> int:
    """
    Calculate MARRIAGE_TO_VILLAGE_ID based on VILLAGE_ID and COUNTER following the specified rules.
    
    :param village_id: Integer representing the village ID (1 or more)
    :param counter: Integer representing the counter (1 or more)
    :return: Integer representing the marriage to village ID
    """
    if not (village_id >= 1):
        raise ValueError("VILLAGE_ID must be 1 or more.")
    if not (counter >= 1):
        raise ValueError("COUNTER must be 1 or more.")
    
    # Reduce counter to range 1-196 using modulo
    counter = ((counter - 1) % 196) + 1
    
    # Determine the block and base add
    block = (counter - 1) // 28
    base_add = 1 + 4 * block
    
    # Determine position within the block
    pos = counter - 28 * block
    
    # Determine the add value based on position
    if pos % 4 == 1 or pos % 4 == 2:
        add = base_add
    else:
        add = base_add + 2
    
    # Determine the base and mod based on village_id range
    base = ((village_id - 1) // 28) * 28
    mod = 28
    
    # Calculate the result using modular arithmetic
    local_id = village_id - base
    result = ((local_id + add - 1) % mod) + 1 + base
    return result