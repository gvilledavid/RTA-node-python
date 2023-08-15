# Intellivue
This project is a simplified version of the [PERSEUS](https://github.com/derekmerck/PERSEUS) project by [derekmerck](https://github.com/derekmerck).  The intention is to use with a mqtt server from a raspberry pi.

## Delay
The maximum delay time is ~3 seconds according to a 10 minute probe using an MP70 at a baudrate of 115200.  In an industry where every second counts, this should be further analyzed for reliability before use on patients.

![Packet Delays](packet_delays.png)


##Legacy packets
Device/Vitals/MACLeafMain1/MAC was the old way of publishing, I am keeping that for now but moving new stuff to Devices/...
Legacy topics:
    Device/Vitals/1245a3bfed12LeafMain1/1245a3bfed12
Legacy messages:
    {'l': [{'n': 'BP_SYS', 'v': 120}, {'n': 'BP_DIA', 'v': 80}, {'n': 'BP', 'v': 90}, {'n': 'F0E5', 'v': 60}, {'n': 'HR', 'v': 60}, {'n': 'RR', 'v': 15}], 'n': 'v', 'v': '1683062501704'}
I imagine the MQTT topics will look like this:
    Devices/
        vitals/ - typical vitals info
        settings/ - typical settings info split from legacy vitals
        pys/ -pysiological monitor info
        waveforms/
        alarms/
        commands/ - set of commands that can be sent to the devices, to be defined later
        responses/ - rsponses such as acknowledgements to commands
        raw/ - raw vent data if desired for storage
        pulse/
    Nodes/
        pulse/
        commands/
        responses/
    Tiers/
        pulse/
        commands/
        responses/        

Devices UID will be the parent mac concatenated with the device, such as 12:45:a3:bf:ed:12:ttyAMA3 each device needs to be able to read or publish to Devices/+/UID only. 

We also talked about shortening the packets to only include the key/value pairs:
vitals topic:
      Devices/pys/12:45:a3:bf:ed:12:ttyAMA3
Packet:
     {'BP_SYS': 120, 'BP_DIA': 80, 'BP': 90, 'F0E5': 60, 'HR': 60, 'RR': 15} 
pulse topic:
      /Devices/pulse/12:45:a3:bf:ed:12:ttyAMA3
pulse:
      {"UID": "12:45:a3:bf:ed:12:ttyAMA3", "DID": "e10000020001", "vent-type": "e10000020001", "baud": 115200, "protocol": "MIB", "parent-node": "12:45:a3:bf:ed:12", "device-status": "DEMO", "timestamp": "1683062501705"}     




