# For removing extraneous fields (ex: reserved fields)
REMOVE_FIELDS = []
PB840_BAUD_RATES = [1200, 2400, 4800, 9600, 19200, 38400, 115200]
V60_BAUD_RATE = [9600, 19200, 115200]

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
