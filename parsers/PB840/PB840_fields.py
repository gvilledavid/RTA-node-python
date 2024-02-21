# For removing extraneous fields (ex: reserved fields)
BOTH_REMOVE_FIELDS = []
PB840_REMOVE_FIELDS = []
PB980_REMOVE_FIELDS = []

PB840_BAUD_RATES = [1200, 2400, 4800, 9600, 19200, 38400, 115200]

PB840_CHECKSUM = [1225, 169]
# For converting important field IDs to named fields
PB840_WEB_STRINGS = {
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
    60: "PBW",
    96: "Cdyn",
    97: "Rdyn",
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
    92: "Cstat",  # Raw?
    102: "NIF",
}
PB980_WEB_STRINGS = {161: "PB980_ETCO2"}
BOTH_ALARMS_SNDF = {
    106: {"message": "Apnea ventilation alarm", "Priority": 2},
    107: {"message": "High exhaled minute volume alarm", "Priority": 2},
    108: {"message": "High exhaled tidal volume alarm", "Priority": 2},
    109: {"message": "High O2\% alarm", "Priority": 2},
    110: {"message": "High inspiratory pressure alarm", "Priority": 2},
    111: {"message": "High ventilator pressure alarm", "Priority": 2},
    112: {"message": "High respiratory rate alarm", "Priority": 2},
    113: {"message": "AC power loss alarm", "Priority": 2},
    114: {"message": "Inoperative battery alarm", "Priority": 2},
    115: {"message": "Low battery alarm", "Priority": 2},
    116: {"message": "Inadvertent Power Off alarm", "Priority": 2},
    117: {"message": "Low exhaled mandatory tidal volume alarm", "Priority": 2},
    118: {"message": "Low exhaled minute volume alarm", "Priority": 2},
    119: {
        "message": "Low exhaled spontaneous tidal volume alarm",
        "Priority": 2,
    },
    120: {"message": "Low O2\% alarm", "Priority": 2},
    121: {"message": "Low air supply pressure alarm", "Priority": 2},
    122: {"message": "Low O2 supply pressure alarm", "Priority": 2},
    123: {"message": "Compressor inoperative alarm", "Priority": 2},
    124: {"message": "Disconnect alarm", "Priority": 2},
    125: {"message": "Severe occlusion alarm", "Priority": 2},
    126: {"message": "Inspiration too long alarm", "Priority": 2},
    127: {"message": "Procedure error alarm", "Priority": 2},
    128: {"message": "Compliance limited tidal volume (VT) alarm", "Priority": 2},
    129: {"message": "High inspired tidal volume", "Priority": 2},
    130: {"message": "High inspired tidal volume", "Priority": 2},
    131: {"message": "High compensation limit (1PCOMP) alarm", "Priority": 2},
    132: {"message": "PAV+™ startup too long alarm", "Priority": 2},
    133: {"message": "PAV+™ R and C not assessed alarm", "Priority": 2},
    134: {"message": "Volume not delivered (VC+) alarm", "Priority": 2},
    135: {"message": "Volume not delivered (VS) alarm", "Priority": 2},
    136: {"message": "Low inspiratory pressure (3PPEAK) alarm", "Priority": 2},
    137: {"message": "Technical malfunction A5", "Priority": 2},
    138: {"message": "Technical malfunction A10", "Priority": 2},
    139: {"message": "Technical malfunction A15", "Priority": 2},
    140: {"message": "Technical malfunction A20", "Priority": 2},
    141: {"message": "Technical malfunction A25", "Priority": 2},
    142: {"message": "Technical malfunction A30", "Priority": 2},
    143: {"message": "Technical malfunction A35", "Priority": 2},
    144: {"message": "Technical malfunction A40", "Priority": 2},
    145: {"message": "Technical malfunction A45", "Priority": 2},
    146: {"message": "Technical malfunction A50", "Priority": 2},
    147: {"message": "Technical malfunction A55", "Priority": 2},
    148: {"message": "Technical malfunction A60", "Priority": 2},
    149: {"message": "Technical malfunction A65", "Priority": 2},
    150: {"message": "Technical malfunction A70", "Priority": 2},
    151: {"message": "Technical malfunction A75", "Priority": 2},
    152: {"message": "Technical malfunction A80", "Priority": 2},
}
PB840_ALARMS_SNDF = {
    153: {"message": "Technical malfunction A85*", "Priority": 2},
}
PB980_ALARMS_SNDF = {
    153: {"message": "High ETCO2 Alarm", "Priority": 2},
    160: {"message": "Prox Inop alarm", "Priority": 2},
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
