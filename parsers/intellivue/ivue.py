import time
import logging

from IntellivueProtocol.RS232 import RS232
from IntellivueProtocol.IntellivueDecoder import IntellivueDecoder
from IntellivueProtocol.IntellivueDistiller import IntellivueDistiller

from extract_response import process_data


class Intellivue:
    def __init__(self, ttyDEV, ttyBaud, mac):
        self.total = 0
        self.initiation_time = time.time()
        self.last_keep_alive = time.time()
        self.KeepAliveTime = 5
        self.successes = 0
        self.attempt_delay = 0.001
        self.wait = 0.2
        self.nonecount = 0
        # pulse info
        self.ttyDEV = ttyDEV
        self.ttyBAUD = ttyBaud
        self.status = "IDLE"
        self.DID = ""
        self.protocol = "MIB"
        self.vent_type = ""
        self.parentmac = mac
        self.legacy_vitals_topic = f"Device/Vitals/{mac.replace(':','').lower()}LeafMain1/{mac.replace(':','').lower()}"
        self.vitals_topic = f"Devices/pys/{mac}:{ttyDEV}"

        if ttyDEV[:3] == "COM":  # windows style
            self.ser = RS232(ttyDEV, ttyBaud)
        else:
            self.ser = RS232(f"/dev/{ttyDEV}", ttyBaud)
        self.ser.socket.timeout = 0.001
        self.ser.socket.writeTimeout = 0.001
        self.fields = {}
        self.last_packet = time.time()
        self.decoder = IntellivueDecoder()
        self.distiller = IntellivueDistiller()
        self.connected = True  # assume it's initially connected

        self.KeepAliveMessage = self.decoder.writeData("MDSSinglePollAction")
        self.AssociationRequest = self.decoder.writeData("AssociationRequest")
        self.AssociationAbort = self.decoder.writeData("AssociationAbort")
        self.ReleaseRequest = self.decoder.writeData("ReleaseRequest")

        dataCollectionTime = 72 * 60 * 60  # seconds
        dataCollection = {"RelativeTime": dataCollectionTime * 8000}
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

        # logging.debug("Association response: {0}".format(self.AssociationResponse))

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
        logging.info("Sent MDS Create Event Result...")
        logging.critical("Connected")
        self.connected = True

    def fields_counter(self, res):
        R = self.decoder.readData(res)
        l, legacy = process_data(R)
        for i in legacy:
            self.fields[i["n"]] = self.fields.get(i["n"], 0) + 1
        print(
            f"{time.time() - self.initiation_time:0.2f}",
            self.successes,
            self.total,
            ",".join([str(self.fields[k]) for k in self.fields]),
        )

    def make_packet(self, res):
        R = self.decoder.readData(res)
        # print(R)
        l, legacy = process_data(R)
        # legacy = [i for i in legacy ]
        packet = {"l": legacy, "n": "v", "v": str(int(time.time() * 1000))}
        logging.info(l)
        return l, packet

    def setup(self):
        while not self.connected:
            self.attempt_connection()
        # self.status="CONNECTED"

    def attempt_connection(self):
        try:
            self.ser.send(self.AssociationRequest)
            logging.info("Sent AssociationRequest")
            time.sleep(self.attempt_delay)
            res, message_type = self.receive()
            logging.info(message_type)
            # logging.debug(res)
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
                    self.status = self.last[0]["MDSCreateInfo"]["MDSAttributeList"][
                        "AttributeList"
                    ]["AVAType"]["NOM_ATTR_MODE_OP"]["AttributeValue"]["OperatingMode"]
                except:
                    pass
                logging.info(message_type)
                # logging.debug(event_message)
                if message_type == "MDSCreateEvent":
                    logging.info("trying to create MDS Event")
                    self.createMDSCreateEvent(res, event_message)
        except:
            logging.warning("Connection attempt failed")
            # need to wait here and try connecting again
            self.DID = ""
            self.status = "DISCONNECT"

    def close(self):
        try:
            self.ser.send(self.AssociationAbort)
            logging.info("Sent Association Abort...")
            self.ser.send(self.ReleaseRequest)
            logging.info("Sent Release Request...")
        except:
            logging.info("Connection wasn't open")
            self.status = "DISCONNECT"
        while True:
            res, message_type = self.receive()
            logging.info("Attempting to close")
            if message_type == None:
                self.connected = False
                break
        logging.critical(
            f"Closing, total uptime was {time.time() - self.initiation_time:0.2f}"
        )
        self.status = "DISCONNECT"

    def receive(self):
        start_time = time.time()
        res = ""
        message_type = ""
        while True:
            time.sleep(self.attempt_delay)
            try:
                res = self.ser.receive()
                elapsed = time.time() - start_time
                logging.debug(f"{time.time() - self.initiation_time:0.2f}")
                if res != b"" or elapsed > self.wait:
                    break
            except:
                logging.error("Exception while trying to receive")
                break
        message_type = self.decoder.getMessageType(res)
        logging.critical(f"{time.time() - self.initiation_time:0.2f} {message_type}")
        # if message type is critical root error then reconnect
        # print(self.decoder.readData(res))
        return res, message_type

    def poll(self):
        try:
            self.total += 1
            if (time.time() - self.last_keep_alive) > (self.KeepAliveTime - 5):
                self.ser.send(self.KeepAliveMessage)
                self.last_keep_alive = time.time()
                logging.info("Sent KeepAliveMessage")

            self.ser.send(self.MDSExtendedPollActionNumeric)
            logging.info("Sent MDSExtendedPollActionNumeric")
            res, message_type = self.receive()
            print(f"{res=}\n{message_type=}")
            if message_type == "AssociationAbort":
                self.connected = False
                self.setup()

            if message_type in [
                "LinkedMDSExtendedPollActionResult" | "MDSExtendedPollActionResult"
            ]:
                # MDSExtendedPollActionResult is usually empty
                # self.fields_counter(res)
                # print(f"{self.successes}/{self.total}/{time.time() - self.initiation_time:0.1f}, {message_type}")
                self.successes += 1
                print(time.time() - self.last_packet, "since last success")
                self.last_packet = time.time()
                l, self.legacy_vitals = self.make_packet(res)
                if len(l) == 0:
                    # sometimes the parsed message is empty?
                    return self.poll()
                return l, False
            return self.poll()
        except:
            return self.poll()

    def pulse(self):
        message = f'\u007b"UID": "{self.parentmac}:{self.ttyDEV}", "DID": "{self.DID}", "vent-type": "{self.vent_type}", "baud": {self.ttyBAUD}, "protocol": "{self.protocol}", "parent-node": "{self.parentmac}", "device-status": "{self.status}", "timestamp": "{str(int(time.time()*1000))}"\u007d'
        topic = f"Devices/pulse/{self.parentmac}:{self.ttyDEV}"
        return topic, message

    def test_run(self):
        while True:
            if self.connected:
                packet, res = self.poll()
                print("vitals topic:\n     ", self.vitals_topic, "\n\n")
                print("Packet:\n    ", packet, "\n\n")
                print("legacy vitals topic:\n     ", self.legacy_vitals_topic, "\n\n")
                print("legacy vitals packet:\n     ", self.legacy_vitals, "\n\n")
                pulse_topic, pulse_message = self.pulse()
                print("pulse topic:\n     ", pulse_topic, "\n\n")
                print("pulse:\n     ", pulse_message, "\n\n\n\n\n")
            time.sleep(self.wait)


if __name__ == "__main__":
    logging.basicConfig(level=logging.CRITICAL)

    # s = Intellivue('ttyAMA3',115200,"12:45:a3:bf:ed:12")
    s = Intellivue("ttyAMA1", 115200, "12:45:a3:bf:ed:12")
    s.test_run()
    s.close()
