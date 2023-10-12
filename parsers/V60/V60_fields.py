# For removing extraneous fields (ex: reserved fields)
V60_REMOVE_FIELDS_SNDA = [
    0,
    2,
    3,
    7,
    8,
    10,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    33,
    35,
    36,
    37,
    46,
    51,
    53,
    54,
    55,
    56,
    57,
    58,
    59,
    60,
    61,
    62,
    63,
    64,
    65,
    66,
    67,
    68,
    69,
    70,
    71,
    72,
    73,
    74,
    75,
    76,
    77,
    78,
    79,
    80,
    83,
    84,
    85,
    86,
    87,
    88,
    90,
    92,
    93,
    94,
    95,
    97,
    98,
]  # TODO: add all reserved or unused fields as well
# VRPT version
V60_REMOVE_FIELDS_VRPT = [
    0,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
    34,
    35,
    36,
    37,
    38,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    50,
    51,
    52,
    61,
    63,
    65,
    67,
    71,
    72,
    74,
    75,
    76,
    78,
    80,
    82,
    83,
    86,
    88,
    90,
    91,
    92,
    93,
    94,
    95,
    96,
    97,
    98,
    99,
    100,
    101,
    112,
    114,
    116,
    117,
    120,
    122,
    124,
    128,
    131,
    132,
    133,
    134,
    135,
]  # TODO: add all reserved or unused fields as well

# PB840_BAUD_RATES = [1200, 2400, 4800, 9600, 19200, 38400, 115200]
V60_BAUD_RATES = [9600, 19200, 115200]
# For converting important field IDs to named fields
V60_CHECKSUM_SNDA = [706, 97]
V60_CHECKSUM_VRPT = [988, 133]
# PB840_CHECKSUM = [1225, 169]
"""PB840_WEB_STRINGS = {
    6: "VtID",
    8: "Type",
    9: "Mode",
    10: "MType",
    11: "SType",
    13: "SetRate",
    14: "SetVT"
    # ,15 : "PFlow"
    ,
    15: "SetFlow",
    16: "SetFIO2",
    18: "SetPEEP",
    31: "SetPSV",
    46: "SetP",
    47: "SetTi",
    94: "Pplat",
    70: "TotBrRate",
    71: "VTe",
    72: "MinVent",
    73: "PIP",
    74: "Ti",
    78: "VTi",
    79: "PEEPi",
    85: "RSBI",
    86: "TiTtot",
    87: "PEEP",
    92: "Raw",
    102: "NIF",
}"""

V60_WEB_STRINGS_SNDA = {
    1: "TIME",
    5: "Mode",
    6: "SetRR",
    9: "SetFI02",
    11: "SetPEEP",
    22: "SetPSV",
    30: "TotBrRate",
    31: "VT",
    32: "MinVent",
    34: "PIP",
}
V60_WEB_STRINGS_VRPT = {
    1: "TIME",
    53: "Mode",
    55: "SetRR",
    64: "SetFI02",
    56: "SetPEEP",
    57: "SetPSV",
    81: "TotBrRate",
    77: "VT",
    79: "MinVent",
    73: "PIP",
}

V60_ALARMS_SNDA = {
    44: {
        "message": "High inhalation pressure",
        "Priority": 2
        # "status" = NORMAL, RESET, ALARM as indicated by vent
        # "vent-code" = index
        # "Time"  str(int(time.time()*1000))
    },
    45: {"message": "Low inhalation pressure", "Priority": 2},
    47: {"message": "Low exhaled mandatory/spontaneous tidal volume", "Priority": 2},
    48: {"message": "Low exhaled minute volume", "Priority": 2},
    49: {"message": "High respiratory rate", "Priority": 2},
    50: {"message": "Low oxygen supply pressure", "Priority": 2},
    52: {"message": "Low battery", "Priority": 2},
    91: {"message": "Occlusion or I-time too long", "Priority": 2},
}


V60_ALARMS_VRPT = {
    102: {"message": "Occlusion", "Priority": 2},
    103: {"message": "Safety valve", "Priority": 2},
    104: {"message": "Low internal battery", "Priority": 2},
    105: {"message": "Nonvolatile memory failure", "Priority": 2},
    106: {"message": "Primary alarm failure", "Priority": 2},
    107: {"message": "High inspiratory pressure alarm sta", "Priority": 2},
    108: {"message": "Apnea", "Priority": 2},
    109: {"message": "Low inspiratory pressure", "Priority": 2},
    110: {"message": "Air source fault", "Priority": 2},
    111: {"message": "O2 valve stuck closed", "Priority": 2},
    113: {"message": "Low O2 supply", "Priority": 2},
    115: {"message": "Low minute volume ", "Priority": 2},
    118: {"message": " Low tidal volume", "Priority": 2},
    119: {"message": " Low spontaneous tidal volume", "Priority": 2},
    121: {"message": "High respiratory rate", "Priority": 2},
    123: {"message": "High enclosure temperature", "Priority": 2},
    125: {"message": "Low PEEP", "Priority": 2},
    126: {"message": "Low EPAP", "Priority": 2},
    127: {"message": "High leak", "Priority": 2},
}

# For producing the proper mode string
MODEMAP = {
    "A/CPC": "A/C-PC",
    "A/CVC": "A/C-VC",
    "A/CVC+": "PRVC",
    "SIMVPCNONE": "SIMV-PC",
    "SIMVPCPS": "SIMV-PC",
    "SIMVPCTC": "SIMV-PC",
    "SIMVVCNONE": "SIMV-VC",
    "SIMVVCPS": "SIMV-VC",
    "SIMVVCTC": "SIMV-VC",
    "SIMVVC+NONE": "PRVC",
    "SIMVVC+PS": "PRVC",
    "SIMVVC+TC": "PRVC",
    "SPONTPCNONE": "CPAP",
    "SPONTPCPS": "PSV",
    "SPONTPCTC": "TUBE",
    "SPONTPCVS": "VAPS",
    "SPONTPCPA": "PAV+",
    "SPONTVCNONE": "CPAP",
    "SPONTVCPS": "PSV",
    "SPONTVCTC": "TUBE",
    "SPONTVCVS": "VAPS",
    "SPONTVCPA": "PAV+",
    "BILEVLPCNONE": "APRV",
    "BILEVLPCPS": "APRV",
    "BILEVLPCTC": "APRV",
}

V60_MODEMAP = {
    "S/T": "SIMV-PC",
    "PCV": "A/C-PC",
    "CPAP": "CPAP",
    "AVAPS": "PRVC",
    "STDBY": "STDBY",
    "PPV": "A/C-PC",
}
