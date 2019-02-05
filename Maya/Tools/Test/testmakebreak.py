
import math

def damm(val):
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

    # interim = 0
    # interim = matrix[interim][math.floor(val/ 100)]
    # interim = matrix[interim][math.floor(val % 100 / 10)]
    # interim = matrix[interim][val % 10]

    # Needs to support 3 or 4 digit numbers, so stringify and loop
    sval = str(int(val))
    interim = 0

    for c in sval:
        interim = matrix[interim][int(c)]

    return interim


def breakAlpha(a):
    """Break alpha value into LOD, Mode, Bump, and Thickness

        Version 2 uses a 4 decimal places, 3 to pack the above
        and the 4th as a checksum value for the packed values.
    """
    # Default value: invalid crease
    lod = -1
    mode = 0
    bump = 0
    thickness = 0

    # Only extract from alphas with a valid checksum
    checksum = damm(math.floor(a * 10000))
    if checksum == 0:
        x = int(math.floor(a * 1000))
        lod = (x & 768) / 256
        mode = (x & 192) / 64
        bump = (x & 32) / 32
        thickness = x & 31

    return (lod, mode, bump, thickness)


def makeAlpha(lod, mode, bump, thickness):
    """Make an alpha value from LOD/mode/bump/thickness"""
    # Re-encode components into a single value
    a = int(lod) * 256 | int(mode) * 64 | int(bump) * 32 | int(thickness)

    print('makeAlpha a: {}'.format(a))

    # Offset to the [0,1) range and append a checksum
    # An extra 0.00001 is added to correct for rounding errors 
    # with pushing between Python and Maya. Unused in decoding.
    checksum = damm(a)
    print('makeAlpha checksum: {}'.format(checksum))

    a = (a * 100.0 + checksum * 10.0 + 1) / 100000.0

    print('makeAlpha final: {}'.format(a))
    return a


a = makeAlpha(0,0,0,31)
print('---')
print(a)
lod, mode, bump, thickness = breakAlpha(a)
print(lod, mode, bump, thickness)

a = makeAlpha(1,0,0,31)
print('---')
print(a)
lod, mode, bump, thickness = breakAlpha(a)
print(lod, mode, bump, thickness)

a = makeAlpha(2,2,1,15)
print('---')
print(a)
lod, mode, bump, thickness = breakAlpha(a)
print(lod, mode, bump, thickness)
