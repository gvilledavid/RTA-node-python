import time
from V60.V60_fields import (
    V60_REMOVE_FIELDS_SNDA,
    V60_WEB_STRINGS_SNDA,
    V60_ALARMS_SNDA,
    V60_CHECKSUM_SNDA,
    V60_MODEMAP,
    V60_ALARMS_VRPT,
    V60_CHECKSUM_VRPT,
    V60_REMOVE_FIELDS_VRPT,
    V60_WEB_STRINGS_VRPT,
)


class V60_Packet_Creator:
    def check_data_type(self, command_name):
        self.V60_REMOVE_FIELDS = None
        self.V60_ALARMS = None
        self.V60_CHECKSUM = None
        self.V60_WEB_STRINGS = None
        self.VRPT_On = None
        if command_name == "MISCA":
            self.V60_REMOVE_FIELDS = V60_REMOVE_FIELDS_SNDA
            self.V60_ALARMS = V60_ALARMS_SNDA
            self.V60_WEB_STRINGS = V60_WEB_STRINGS_SNDA
            self.V60_CHECKSUM = V60_CHECKSUM_SNDA
            self.VRPT_On = False
        elif command_name == "VRPT":
            self.V60_REMOVE_FIELDS = V60_REMOVE_FIELDS_VRPT
            self.V60_ALARMS = V60_ALARMS_VRPT
            self.V60_WEB_STRINGS = V60_WEB_STRINGS_VRPT
            self.V60_CHECKSUM = V60_CHECKSUM_VRPT
            self.VRPT_On = True
            return True
        else:
            raise Exception
        return False

    def get_data_as_fields(self, data):
        """Create list of [field ID, value] from the V60 datagram"""
        # TODO, Remove unimportant fields
        # -5 for access
        # print(data)
        header, fields_b = data.split(b",\x02")
        command_name, n_chars, n_fields = header.decode().split(",")
        fields_b = fields_b.replace(b"\x03\r", b"")
        # format for VRPT and SNDA are off by one ','
        # the following statement corrects the difference
        if self.check_data_type(command_name):
            fields_b = fields_b[1:-1]
        fields = [i.strip() for i in fields_b.decode().split(",")[:-1]]
        # print(f"checksums = {n_chars}, {n_fields}")
        # TODO: verify miscf is miscf, verify checksums
        # print(len(fields_b), len(fields))
        if (
            len(fields_b) != self.V60_CHECKSUM[0]
            or len(fields) != self.V60_CHECKSUM[1]
            or int(n_chars.strip()) != self.V60_CHECKSUM[0]
            or int(n_fields.strip()) != self.V60_CHECKSUM[1]
        ):
            # create_packet(0, False)
            raise Exception
        raw = [[0, command_name]]
        raw.extend([[i + 1, v.strip()] for i, v in enumerate(fields)])
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
        # raw[5 - 2][1] = raw[5 - 2][1][1:]
        # Convert mode string
        # raw[9 - 2][1] = V60_MODEMAP[raw[9 - 2][1] + raw[10 - 2][1] + raw[11 - 2][1]]
        # convert VTe and VTi to mL from L
        # raw[71 - 2][1] = to_mL(raw[71 - 2][1])  # VTe
        # raw[78 - 2][1] = to_mL(raw[78 - 2][1])  # VTi
        # raw[14 - 2][1] = to_mL(raw[14 - 2][1])  # setVT
        if self.VRPT_On:
            raw[54][1] = V60_MODEMAP[raw[54][1]]
            raw[77][1] = self.to_mL(raw[77][1])  # VT
            #raw[79][1] = self.to_mL(raw[79][1])  # MinVent
        else:
            raw[5][1] = V60_MODEMAP[raw[5][1]]
            raw[31][1] = self.to_mL(raw[31][1])  # VT
            #raw[32][1] = self.to_mL(raw[32][1])  # MinVent`

    def set_webstrings(self, raw):
        """Convert important field IDs to named fields"""
        for i in range(len(raw)):
            if raw[i][0] in self.V60_WEB_STRINGS:
                raw[i][0] = self.V60_WEB_STRINGS[raw[i][0]]
            # else we could remove here

    def set_fspon(self, raw):
        """set fpons = TotBrRate - SetRate (or 0 if negative)"""
        try:
            if self.VRPT_On:
                fspon = max(0, float(raw[81][1]) - float(raw[55][1]))
                # res.append({"n": "fspon", "v": f"{fspon:0.6f}"})
            else:
                fspon = max(0, float(raw[30][1]) - float(raw[6][1]))
                # res.append({"n": "fspon", "v": f"{fspon:0.6f}"})
            raw.append(["fspon", fspon])
            return True
        except:
            # probably not numeric
            return False

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
            if field[0] in self.V60_ALARMS:
                if verbose or field[1] != "NORMAL":
                    alarm = self.V60_ALARMS.get(
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
        """Create a packet from raw V60 ventilator output"""
        # need to correct for offset between split string and PB fields
        try:
            raw = self.get_data_as_fields(data)
            self.set_corrections(raw)
            self.set_fspon(raw)
            raw = [i for i in raw if i[0] not in self.V60_REMOVE_FIELDS]
            self.set_webstrings(raw)
            legacy_res = [{"n": str(i[0]), "v": i[1]} for i in raw]
            # print(raw)
            alarms = self.create_alarms_packet(raw, debug)

            return (
                {"l": legacy_res, "n": "v", "v": str(int(time.time() * 1000))},
                alarms,
                False,
            )
        except:
            return {"n": "v", "v": str(int(time.time() * 1000))}, [], True
