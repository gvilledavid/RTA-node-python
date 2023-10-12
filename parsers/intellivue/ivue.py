import time
import logging

from IntellivueProtocol.RS232 import RS232
from IntellivueProtocol.IntellivueDecoder import IntellivueDecoder
from IntellivueProtocol.IntellivueDistiller import IntellivueDistiller

from extract_response import process_data


class Intellivue:
    def __init__(self, ttyDEV, ttyBaud, mac, logger):
        self.logger = logger
        self.total = 0
        self.initiation_time = time.monotonic()
        self.last_keep_alive = time.monotonic()
        self.KeepAliveTime = 8
        self.successes = 0
        self.attempt_delay = 0.5
        self.wait = 0.75
        self.send_freq = 10
        self.nonecount = 0
        # pulse info
        self.ttyDEV = ttyDEV
        self.ttyBAUD = ttyBaud
        self.bedlabel = "Intellivue"
        self.mode = "IDLE"
        self.status = "DISCONNECTED"
        self.DID = ""
        self.protocol = "MIB"
        self.vent_type = ""
        self.manufacturer = ""
        self.UID = f"{mac}:{ttyDEV}"
        self.parentmac = mac
        self.legacy_vitals_topic = f"Device/Vitals/{mac.replace(':','').lower()}LeafMain1/{mac.replace(':','').lower()}"
        self.vitals_topic = f"Devices/phys/{self.UID}"
        if ttyDEV[:3] == "COM":  # windows style
            self.ser = RS232(ttyDEV, ttyBaud)
        else:
            self.ser = RS232(f"/dev/{ttyDEV}", ttyBaud)
        self.ser.socket.timeout = 0.1
        self.ser.socket.write_timeout = 0.1
        # self.ser.socket.writeTimeout = 0.1

        self.fields = {}
        self.last_packet = time.monotonic() - 10
        self.decoder = IntellivueDecoder()
        self.distiller = IntellivueDistiller()
        self.connected = False
        # Association=['option_list'] ['supported_aprofiles']['AttributeList'] ['AVAType']['NOM_POLL_PROFILE_SUPPORT'] ['AttributeValue' ]['PollProfileSupport']['PollProfileSupport_optional_packages'] ['AttributeList']['AVAType'] ['NOM_ATTR_POLL_PROFILE_EXT']['AttributeValue'] ['PollProfileExt']['PollProfileExtOptions']='POLL1SECANDWAVEANDLISTANDDYN',

        self.KeepAliveMessage = self.decoder.writeData("MDSSinglePollAction")
        self.AssociationRequest = self.decoder.writeData("AssociationRequest")
        self.AssociationAbort = self.decoder.writeData("AssociationAbort")
        self.ReleaseRequest = self.decoder.writeData("ReleaseRequest")

        self._error_count = 0
        self._max_error_count = 20

        dataCollectionTime = 72 * 60 * 60 * 2  # seconds
        dataCollection = {
            "RelativeTime": 1  # dataCollectionTime * 8000,
            # "PollProfileExtOptions": "POLL_EXT_PERIOD_NU_AVG_12SEC",
        }
        self.MDSExtendedPollActionNumeric = self.decoder.writeData(
            "MDSExtendedPollActionNUMERIC", dataCollection
        )
        # self.MDSExtendedPollActionWave = self.decoder.writeData('MDSExtendedPollActionWAVE', dataCollection)
        # self.MDSExtendedPollActionAlarm = self.decoder.writeData('MDSExtendedPollActionALARM', dataCollection)
        # desiredWaveParams = {'TextIdLabel': ["Pleth", "ECG"]}
        # self.MDSSetPriorityListWave = self.decoder.writeData('MDSSetPriorityListWAVE', desiredWaveParams)

        self.close()
        self.setup()

    def createMDSCreateEvent(self, association_message, event_message):
        # Grabbed from PERSEUS PhilipsTelemetryStream.py
        self.AssociationResponse = self.decoder.readData(association_message)

        self.logger.debug("Association response: {0}".format(self.AssociationResponse))

        self.KeepAliveTime = (
            self.AssociationResponse["AssocRespUserData"]["MDSEUserInfoStd"][
                "supported_aprofiles"
            ]["AttributeList"]["AVAType"]["NOM_POLL_PROFILE_SUPPORT"]["AttributeValue"][
                "PollProfileSupport"
            ][
                "min_poll_period"
            ][
                "RelativeTime"
            ]
            / 8000
        )
        self.MDSCreateEvent, self.MDSParameters = self.decoder.readData(event_message)

        # Store the absolute time marker that everything else will reference
        self.initialTime = self.MDSCreateEvent["MDSCreateInfo"]["MDSAttributeList"][
            "AttributeList"
        ]["AVAType"]["NOM_ATTR_TIME_ABS"]["AttributeValue"]["AbsoluteTime"]
        self.relativeInitialTime = self.MDSCreateEvent["MDSCreateInfo"][
            "MDSAttributeList"
        ]["AttributeList"]["AVAType"]["NOM_ATTR_TIME_REL"]["AttributeValue"][
            "RelativeTime"
        ]
        if "saveInitialTime" in dir(self.distiller):
            self.distiller.saveInitialTime(self.initialTime, self.relativeInitialTime)

        # Send MDS Create Event Result
        self.MDSCreateEventResult = self.decoder.writeData(
            "MDSCreateEventResult", self.MDSParameters
        )
        self.ser.send(self.MDSCreateEventResult)
        self.logger.info("Sent MDS Create Event Result...")
        self.logger.critical("Connected")
        self.connected = True

    def fields_counter(self, res):
        R = self.decoder.readData(res)
        l, legacy = process_data(R, self.logger)
        for i in legacy:
            self.fields[i["n"]] = self.fields.get(i["n"], 0) + 1
        print(
            f"{time.monotonic() - self.initiation_time:0.2f}",
            self.successes,
            self.total,
            ",".join([str(self.fields[k]) for k in self.fields]),
        )

    def make_packet(self, res):
        R = self.decoder.readData(res)
        try:
            rorls_type = R["ROLRSapdu"]["RolrsId"]["state"]
            #'RORLS_FIRST'
            #'RORLS_NOT_FIRST_NOT_LAST'
            #'RORLS_LAST
        except:
            rorls_type = None
        l, legacy = process_data(R, self.logger)
        # legacy = [i for i in legacy ]
        # packet = {"l": legacy, "n": "v", "v": str(int(time.time() * 1000))}
        self.logger.info(l)
        return l, rorls_type

    def setup(self, reattempt=False, reattempt_res=None):
        self.idle = True
        self.initial_connection_timout = 10
        self.initial_connection_attempt = time.monotonic()
        self.status = "DISCONNECTED"
        self.logger.info("Attempting connection")
        while not self.connected and time.monotonic() < (
            self.initial_connection_attempt + self.initial_connection_timout
        ):
            if not reattempt:
                self.ser.socket.flushInput()
                self.ser.socket.flushOutput()
                self.attempt_connection()
                time.sleep(0.5)
            else:
                self.attempt_connection(
                    reattempt=reattempt, reattempt_res=reattempt_res
                )
        if self.status != "DISCONNECTED":
            self.logger.info(
                f"Detected:\n{self.manufacturer=}\n{self.DID=}\n{self.vent_type=}\n{self.bedlabel=}\n{self.mode=}\n{self.status=}"
            )
            self._error_count = 0
            time.sleep(1)
            self.idle = True
            self.logger.info("MDSExtendedPollActionNumeric")
            return True
        return False

    def attempt_connection(
        self,
        reattempt=False,
        reattempt_res=None,
    ):
        try:
            if not reattempt:
                self.ser.send(self.AssociationRequest)
                self.logger.info("Sent AssociationRequest")
                time.sleep(self.attempt_delay)
                res, message_type = self.receive()
                self.logger.info(message_type)
                # self.logger.debug(res)
            else:
                res = reattempt_res
            if message_type == "AssociationResponse":
                event_message = self.ser.receive()
                message_type = self.decoder.getMessageType(event_message)
                try:
                    self.last = self.decoder.readData(event_message)
                    self.manufacturer = "".join(
                        [
                            str(f"{i:#04x}")[2:4]
                            for i in self.last[0]["MDSCreateInfo"]["MDSAttributeList"][
                                "AttributeList"
                            ]["AVAType"]["NOM_ATTR_ID_MODEL"]["AttributeValue"][
                                "SystemModel"
                            ][
                                "manufacturer"
                            ][
                                "VariableLabel"
                            ][
                                "value"
                            ]
                        ]
                    )
                    # print(self.last)
                    self.DID = "".join(
                        [
                            str(f"{i:#04x}")[2:4]
                            for i in self.last[0]["MDSCreateInfo"]["MDSAttributeList"][
                                "AttributeList"
                            ]["AVAType"]["NOM_ATTR_SYS_ID"]["AttributeValue"][
                                "VariableLabel"
                            ][
                                "value"
                            ]
                        ]
                    )
                    self.vent_type = "".join(
                        [
                            str(f"{i:#04x}")[2:4]
                            for i in self.last[0]["MDSCreateInfo"]["MDSAttributeList"][
                                "AttributeList"
                            ]["AVAType"]["NOM_ATTR_ID_MODEL"]["AttributeValue"][
                                "SystemModel"
                            ][
                                "model_number"
                            ][
                                "VariableLabel"
                            ][
                                "value"
                            ]
                        ]
                    )
                    self.bedlabel = self.last[0]["MDSCreateInfo"]["MDSAttributeList"][
                        "AttributeList"
                    ]["AVAType"]["NOM_ATTR_ID_BED_LABEL"]["AttributeValue"]["String"][
                        "value"
                    ].rstrip(
                        "\x00"
                    )
                    self.mode = self.last[0]["MDSCreateInfo"]["MDSAttributeList"][
                        "AttributeList"
                    ]["AVAType"]["NOM_ATTR_MODE_OP"]["AttributeValue"]["OperatingMode"]
                    self.status = self.last[0]["MDSCreateInfo"]["MDSAttributeList"][
                        "AttributeList"
                    ]["AVAType"]["NOM_ATTR_VMS_MDS_STAT"]["AttributeValue"]["MDSStatus"]
                    if self.vent_type == "e10000020001":
                        self.vent_type = "Intellivue"
                except:
                    pass
                self.logger.info(message_type)
                self.logger.debug(event_message)
                if message_type == "MDSCreateEvent":
                    self.logger.info("trying to create MDS Event")
                    self.createMDSCreateEvent(res, event_message)
        except:
            self.logger.warning("Connection attempt failed")
            # need to wait here and try connecting again
            self.DID = ""
            self.status = "DISCONNECTED"

    def close(self):
        try:
            self.ser.send(self.AssociationAbort)
            self.logger.info("Sent Association Abort...")
            self.ser.send(self.ReleaseRequest)
            self.logger.info("Sent Release Request...")
        except:
            self.logger.info("Connection wasn't open")
            self.status = "DISCONNECTED"
        while True:
            res, message_type = self.receive()
            # self.logger.info("Attempting to close")
            if message_type == None:
                self.connected = False
                break
        self.logger.critical(
            f"Closing, total uptime was {time.monotonic() - self.initiation_time:0.2f}"
        )
        time.sleep(1)
        self.ser.socket.flushInput()
        self.ser.socket.flushOutput()
        self.status = "DISCONNECTED"

    def receive(self):
        start_time = time.monotonic()
        res = ""
        message_type = ""
        self.logger.debug(
            f"{time.monotonic() - self.initiation_time:0.2f} Try to receive"
        )
        while True:
            time.sleep(self.attempt_delay / 2)
            try:
                res = self.ser.receive()
                elapsed = time.monotonic() - start_time
                if res != b"" or elapsed > self.wait:
                    self.logger.debug(
                        f"{time.monotonic() - self.initiation_time:0.2f} timeout"
                    )
                    break
            except:
                self.logger.error("Exception while trying to receive")
                break
        message_type = self.decoder.getMessageType(res)
        if message_type == "TimeoutError" or not res or not message_type:
            self._error_count = self._error_count + 1
        self.logger.critical(
            f"{time.monotonic() - self.initiation_time:0.2f} {message_type}"
        )
        # if message type is critical root error then reconnect
        # print(self.decoder.readData(res))
        return res, message_type

    def poll(self):
        try:
            self.total += 1
            if (time.monotonic() - self.last_keep_alive) > (self.KeepAliveTime - 5):
                self.ser.send(self.KeepAliveMessage)
                self.last_keep_alive = time.monotonic()
                self.logger.info("Sent KeepAliveMessage")
            if self.idle:
                self.ser.send(self.MDSExtendedPollActionNumeric)
                self.last_keep_alive = time.monotonic()
                self.idle = False
            res, message_type = self.receive()
            if self._error_count > self._max_error_count:
                self.logger.critical(
                    f"Intellivue failed to respond for too long. Reinitializing."
                )
                self.close()
                self.setup()

                return None, False
            # print(f"\n\n\n{message_type=}\n{self.decoder.readData(res)=}")
            match message_type:
                case None:
                    # empty response or timeout
                    pass
                case "AssociationResponse":
                    self.connected = False
                    self.setup(reattempt=True, reattempt_res=res)
                case "MDSCreateEvent":
                    self.logger.info(
                        f"Association Request acknowledged with MDSCreatetevent"
                    )
                case "AssociationAbort":
                    self.setup()
                case "LinkedMDSExtendedPollActionResult":
                    vit, rorls_type = self.make_packet(res)
                    match rorls_type:
                        case "RORLS_FIRST":
                            self.vitals_dict = vit
                            self.debug_vitals = [vit]
                        case "RORLS_NOT_FIRST_NOT_LAST":
                            self.vitals_dict.update(vit)
                            self.debug_vitals.append(vit)
                        case "RORLS_LAST":
                            self.vitals_dict.update(vit)
                            self.debug_vitals.append(vit)
                            # filter based on leaf interface settings
                            legacy = [
                                dict(n=vit_key, v=self.vitals_dict[vit_key])
                                for vit_key in self.vitals_dict
                            ]
                            self.legacy_vitals = {
                                "l": legacy,
                                "n": "v",
                                "v": str(int(time.time() * 1000)),
                            }
                            self.vitals_dict["Timestamp"] = str(int(time.time() * 1000))
                            self.vitals_dict["UID"] = f"{self.UID}"
                            print(
                                time.monotonic() - self.last_packet,
                                "since last success",
                            )
                            self.last_packet = time.monotonic()
                            self.successes += 1
                            return self.vitals_dict, False
                        case _:
                            # error?
                            return None, True
                # return self.poll()
                case "MDSExtendedPollActionResult":
                    self.make_packet(res)
                    self.vitals_dict = {}
                    self.debug_vitals = []
                    self.idle = True
                    pass
                case "MDSSinglePollActionResult":
                    self.logger.info("Keep alive acknowledged")
                case _:
                    return None, True
        except Exception as e:
            # return self.poll()
            self.logger.critical(f"Error in poll in ivue.py: \n{e}")
            return None, True
        return None, False

    def pulse(self):
        message = f'\u007b"UID": "{self.UID}", "DID": "{self.DID}", "VentType": "{self.vent_type}", "Baud": {self.ttyBAUD}, "Protocol": "{self.protocol}", "ParentNode": "{self.parentmac}", "DeviceStatus": "{self.mode}", "MDSstatus":"{self.status}","MDSmode":"{self.mode}","BedLabel":"{self.bedlabel}","Timestamp": "{str(int(time.time()*1000))}"\u007d'
        topic = f"Pulse/leafs/{self.UID}:{self.ttyDEV}"
        return topic, message

    def test_run(self):
        while True:
            if self.connected:
                packet, err = self.poll()
                if packet:
                    print("vitals topic:\n     " + self.vitals_topic)
                    print("Packet:\n    ", packet, "\n")
                    # print("legacy vitals topic:\n     "+ self.legacy_vitals_topic+ "\n\n")
                    # print("legacy vitals packet:\n     ", self.legacy_vitals, "\n\n")
                    pulse_topic, pulse_message = self.pulse()
                    print("pulse topic:\n     " + pulse_topic)
                    print("pulse:\n     ", pulse_message, "\n")
            else:
                # try connecting again?
                self.close()
                self.setup()
            time.sleep(self.wait)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    s = Intellivue("ttyAMA1", 115200, "12:45:a3:bf:ed:12", logging)
    s.test_run()
    s.close()
