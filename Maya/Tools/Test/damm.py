
import math
from random import random, randint

# Damm Algorithm matrix is sourced from:
# https://en.wikibooks.org/wiki/Algorithm_Implementation/Checksums/Damm_Algorithm#Python
matrix = (
    (0, 3, 1, 7, 5, 9, 8, 6, 4, 2),
    (7, 0, 9, 2, 1, 5, 4, 8, 6, 3),
    (4, 2, 0, 6, 8, 7, 1, 3, 5, 9),
    (1, 7, 5, 0, 9, 8, 3, 4, 2, 6),
    (6, 1, 2, 3, 0, 4, 5, 9, 7, 8),
    (3, 6, 7, 4, 2, 0, 9, 5, 8, 1),
    (5, 8, 6, 9, 7, 2, 0, 1, 3, 4),
    (8, 9, 4, 5, 3, 6, 2, 0, 1, 7),
    (9, 4, 3, 8, 6, 1, 7, 2, 0, 5),
    (2, 5, 8, 1, 4, 3, 6, 7, 9, 0)
)

for i in range(50): 
    lod = randint(0, 2) # 0, 1, 2 (2 bits)
    mode = randint(0, 2) # 0, 1, 2 (2 bits)
    bump = randint(0, 1) # 0 or 1 (1 bit)
    thickness = round(random() * 31) # 0 -> 31 range (5 bits)

    # Encode components into a single value
    x = lod * 256 | mode * 64 | bump * 32 | thickness

    # Calculate a checksum of the encoded
    interim = 0
    interim = matrix[interim][math.floor(x / 100)]
    interim = matrix[interim][math.floor(x % 100 / 10)]
    interim = matrix[interim][x % 10]
    
    # Offset to the 0.0->1.0 range
    # An extra 0.00001 is added to correct for rounding errors with
    # publishing between Python and Maya. Unused in decoding.
    result = (x * 100 + interim * 10 + 1) / 100000

    # ---

    # Calculate checksum
    full = math.floor(result * 10000)

    interim = 0
    interim = matrix[interim][math.floor(full / 1000)]
    interim = matrix[interim][math.floor(full % 1000 / 100)]
    interim = matrix[interim][math.floor(full % 100 / 10)]
    interim = matrix[interim][full % 10]

    # Extract components 
    d = math.floor(result * 1000)
    lod2 = (d & 768) / 256
    mode2 = (d & 192) / 64
    bump2 = (d & 32) / 32
    thickness2 = d & 31

    print('---')
    print(result, full, interim)
    print(lod, lod2)
    print(mode, mode2)
    print(bump, bump2)
    print(thickness, thickness2)

    # Stop running tests on any failure
    assert(interim == 0)
    assert(lod == lod2)
    assert(mode == mode2)
    assert(bump == bump2)
    assert(thickness == thickness2)
