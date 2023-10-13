import time
from PB840.PB840_fields import (
    PB840_WEB_STRINGS,
    PB980_WEB_STRINGS,
    PB840_CHECKSUM,
    MODEMAP,
    BOTH_REMOVE_FIELDS,
    PB840_REMOVE_FIELDS,
    PB980_REMOVE_FIELDS,
    BOTH_ALARMS_SNDF,
    PB980_ALARMS_SNDF,
    PB840_ALARMS_SNDF,
)

# from PB840.PB840_datagram import datagrams


class PB840_Packet_Creator:
    def check_device_type(self, ID):
        self.EXTENDED_ALARMS = None
        self.WEB_STRINGS = None
        self.EXTENDED_REMOVE_FIELDS = None
        if ID[0:3] == "980":
            EXTENDED_ALARMS = BOTH_ALARMS_SNDF + PB980_ALARMS_SNDF
            self.WEB_STRINGS = PB840_WEB_STRINGS + PB980_WEB_STRINGS
            self.EXTENDED_REMOVE_FIELDS = BOTH_REMOVE_FIELDS + PB980_REMOVE_FIELDS
        else:  # elif ID[0:3] == "840":
            EXTENDED_ALARMS = BOTH_ALARMS_SNDF + PB840_ALARMS_SNDF
            self.WEB_STRINGS = PB840_WEB_STRINGS
            self.EXTENDED_REMOVE_FIELDS = BOTH_REMOVE_FIELDS + PB840_REMOVE_FIELDS

    def get_data_as_fields(self, data):
        """Create list of [field ID, value] from the PB840 datagram"""
        # TODO, Remove unimportant fields
        # -5 for access
        print(data)
        header, fields_b = data.split(b",\x02")
        miscf, n_chars, n_fields = header.decode().split(",")
        fields_b = fields_b.replace(b"\x03\r", b"")
        fields = [i.strip() for i in fields_b.decode().split(",")[:-1]]
        print(f"checksums = {n_chars}, {n_fields}")
        print(len(fields_b), len(fields))
        if (
            len(fields_b) != PB840_CHECKSUM[0]
            or len(fields) != PB840_CHECKSUM[1]
            or int(n_chars.strip()) != PB840_CHECKSUM[0]
            or int(n_fields.strip()) != PB840_CHECKSUM[1]
        ):
            # create_packet(0, False)
            raise Exception
        self.check_device_type(fields_b[6][1][0:3])
        raw = [
            [i + 2, v.strip()] if 2 < i else [i + 1, v.strip()]
            for i, v in enumerate(data.decode().split(","))
        ]
        raw = [i for i in raw if i[0] not in REMOVE_FIELDS]
        return raw

    def to_mL(self, value):
        """Try to convert from L to mL"""
        try:
            return str(float(value) * 1000)
        except:
            return ""

    def set_corrections(self, raw):
        """correct Time, Mode, VTe, and VTi (fields 5,9,71,78)"""
        # parse time
        raw[5 - 2][1] = raw[5 - 2][1][1:]
        # Convert mode string
        raw[9 - 2][1] = MODEMAP[raw[9 - 2][1] + raw[10 - 2][1] + raw[11 - 2][1]]
        # convert VTe and VTi to mL from L
        raw[71 - 2][1] = self.to_mL(raw[71 - 2][1])  # VTe
        raw[78 - 2][1] = self.to_mL(raw[78 - 2][1])  # VTi
        raw[14 - 2][1] = self.to_mL(raw[14 - 2][1])  # setVT

    def set_webstrings(self, raw):
        """Convert important field IDs to named fields"""
        for i in range(len(raw)):
            if raw[i][0] in self.WEB_STRINGS:
                raw[i][0] = self.WEB_STRINGS[raw[i][0]]

    def set_fspon(self, raw):
        """set fpons = TotBrRate - SetRate (or 0 if negative)"""
        TotBrRate = raw[70 - 2][1]
        SetRate = raw[13 - 2][1]
        if TotBrRate.isnumeric() and SetRate.isnumeric():
            fspon = max(0, float(TotBrRate) - float(SetRate))
            raw.append(["fspon", fspon])
        # else nothing is sent

    def check_alarm(self, raw, i, debug):
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

    def set_ifalarm_active(self, raw, res, debug):
        """Check if one of the alarms triggered, skip webstrings"""
        AnyAlarmActive = 0
        for i in range(len(raw)):
            if type(raw[i][0]) == int:
                if self.check_alarm(raw, i, debug):
                    AnyAlarmActive = 1
        res.append({"n": "AnyAlarmActive", "v": str(AnyAlarmActive)})

    def create_alarms_packet(self, raw, verbose=False):
        alarms = []
        for field in raw:
            if field[0] in self.EXTENDED_ALARMS:
                if verbose or field[1] != "NORMAL":
                    alarm = self.EXTENDED_ALARMS.get(
                        field[0], {"message": "Unknown alarm", "Priority": 1}
                    )
                    alarms.append(
                        {
                            "message": alarm["message"],
                            "Priority": alarm["Priority"],
                            "status": field[1],
                            "vent-code": field[0],
                            "Time": str(int(time.time() * 1000)),
                        }
                    )
        return alarms

    def create_packet(self, data, debug=False):
        """Create a packet from raw PB840 ventilator output"""
        # need to correct for offset between split string and PB fields
        try:
            raw = self.get_data_as_fields(data)
            self.set_corrections(raw)
            self.set_fspon(raw)
            self.set_webstrings(raw)
            # raw = [i for i in raw if i[0] not in self.EXTENDED_REMOVE_FIELDS]
            legacy_res = [{"n": str(i[0]), "v": i[1]} for i in raw]
            alarms = self.create_alarms_packet(raw, True)

            # self.set_ifalarm_active(raw, legacy_res, debug)

            return (
                {"l": legacy_res, "n": "v", "v": str(int(time.time() * 1000))},
                alarms,
                False,
            )
        except:
            return {"n": "v", "v": str(int(time.time() * 1000))}, [], True
