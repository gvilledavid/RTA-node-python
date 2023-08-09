import time
from PB840.PB840_fields import PB840_WEB_STRINGS, PB840_CHECKSUM, MODEMAP, REMOVE_FIELDS
from PB840.PB840_datagram import datagrams


def get_data_as_fields(data):
    """Create list of [field ID, value] from the PB840 datagram"""
    # TODO, Remove unimportant fields
    # -5 for access
    print(data)
    header, fields_b = data.split(b",\x02")
    miscf, n_chars, n_fields = header.decode().split(",")
    fields_b = fields_b.replace(b"\x03\r", b"")
    fields = [i.strip() for i in fields_b.decode().split(",")[:-1]]
    print(f"checksums = {n_chars}, {n_fields}")
    # TODO: verify miscf is miscf, verify checksums
    print(len(fields_b), len(fields))
    if len(fields_b) != PB840_CHECKSUM[0] or len(fields) != PB840_CHECKSUM[1]:
        # create_packet(0, False)
        raise Exception
    raw = [
        [i + 2, v.strip()] if 2 < i else [i + 1, v.strip()]
        for i, v in enumerate(data.decode().split(","))
    ]
    raw = [i for i in raw if i[0] not in REMOVE_FIELDS]
    return raw


def to_mL(value):
    """Try to convert from L to mL"""
    try:
        return str(float(value) * 1000)
    except:
        return ""


def set_corrections(raw):
    """correct Time, Mode, VTe, and VTi (fields 5,9,71,78)"""
    # parse time
    raw[5 - 2][1] = raw[5 - 2][1][1:]
    # Convert mode string
    raw[9 - 2][1] = MODEMAP[raw[9 - 2][1] + raw[10 - 2][1] + raw[11 - 2][1]]
    # convert VTe and VTi to mL from L
    raw[71 - 2][1] = to_mL(raw[71 - 2][1])  # VTe
    raw[78 - 2][1] = to_mL(raw[78 - 2][1])  # VTi
    raw[14 - 2][1] = to_mL(raw[14 - 2][1])  # setVT


def set_webstrings(raw):
    """Convert important field IDs to named fields"""
    for i in range(len(raw)):
        if raw[i][0] in PB840_WEB_STRINGS:
            raw[i][0] = PB840_WEB_STRINGS[raw[i][0]]


def set_fspon(raw, res):
    """set fpons = TotBrRate - SetRate (or 0 if negative)"""
    TotBrRate = raw[70 - 2][1]
    SetRate = raw[13 - 2][1]
    if TotBrRate.isnumeric() and SetRate.isnumeric():
        fspon = max(0, float(TotBrRate) - float(SetRate))
        res.append({"n": "fspon", "v": f"{fspon:0.6f}"})
    # else nothing is sent


def check_alarm(raw, i, debug):
    """Alarm if: in [106..153] and not NORMAL or RESET"""
    # check the alarm fields 106 to 153
    inrange = 106 <= raw[i][0] and raw[i][0] <= 153
    # it's an alarm if it's something other than NORMAL or RESET
    isalarm = raw[i][1] not in ["NORMAL", "RESET"]
    # Oxygen O_2 sensor is always LOW in testing
    O2_debug_ignore = raw[i][0] != 122
    if debug:
        return inrange and isalarm and O2_debug_ignore  # (For testing)
    else:
        return inrange and isalarm


def set_ifalarm_active(raw, res, debug):
    """Check if one of the alarms triggered, skip webstrings"""
    AnyAlarmActive = 0
    for i in range(len(raw)):
        if type(raw[i][0]) == int:
            if check_alarm(raw, i, debug):
                AnyAlarmActive = 1
    res.append({"n": "AnyAlarmActive", "v": str(AnyAlarmActive)})


def create_packet(data, debug=False):
    """Create a packet from raw PB840 ventilator output"""
    # need to correct for offset between split string and PB fields
    try:
        raw = get_data_as_fields(data)
        set_corrections(raw)
        set_webstrings(raw)
        # print(raw)

        # generate result and add
        legacy_res = [{"n": str(i[0]), "v": i[1]} for i in raw]

        set_fspon(raw, legacy_res)
        set_ifalarm_active(raw, legacy_res, debug)

        return {"l": legacy_res, "n": "v", "v": str(int(time.time() * 1000))}, False
    except:
        return {"n": "v", "v": str(int(time.time() * 1000))}, True


if __name__ == "__main__":
    for dg in datagrams:
        print("example =", create_packet(dg, True))
