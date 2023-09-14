from response import example_response

desired_fields = {
    "NOM_ECG_CARD_BEAT_RATE": "HR",  # "4182", #pg116 HR
    "NOM_PULS_OXIM_SAT_O2": "SPO2",  # "4BB8", #pg118 SPO2
    "NOM_PRESS_BLD_NONINV_SYS": "BP_SYS",  # "4A05", #pg120 NBP
    "NOM_PRESS_BLD_NONINV_DIA": "BP_DIA",  # "4A06", #pg120 NBP
    "NOM_PRESS_BLD_NONINV_MEAN": "BP",  # "4A07", #pg120 NBP
    "NOM_AWAY_CO2_ET": "ETCO2",  # "50B0", #pg147 CO2
    "NOM_RESP_RATE": "RR",  # "500A", #pg148 RR
    "NOM_PRESS_BLD_NONINV_PULS_RATE": "F0E5",  # pg120 Pulse
    "NOM_PRESS_INTRA_CRAN_MEAN": "580B",  # pg122 ICP
    "NOM_PLETH_PULS_RATE": "4822",  # pg119 Pulse
    "NOM_PULS_OXIM_PERF_REL": "4BB0",  # pg119 Perf
}


# NOM_PRESS_BLD_NONINV_SYS         120      mmHg ( mm mercury )
# NOM_PRESS_BLD_NONINV_DIA         80       mmHg ( mm mercury )
# NOM_PRESS_BLD_NONINV_MEAN        90       mmHg ( mm mercury )
# NOM_PRESS_BLD_NONINV_PULS_RATE   60       bpm ( beats per minute used e.g. for HR/PULSE )
# NOM_ECG_CARD_BEAT_RATE           60       bpm ( beats per minute used e.g. for HR/PULSE )
# NOM_RESP_RATE                    15       rpm ( respiration breathes per minute )
# NOM_PRESS_INTRA_CRAN_MEAN        9        mmHg ( mm mercury )
# NOM_PULS_OXIM_SAT_O2             95.0     % ( percentage )
# NOM_PLETH_PULS_RATE              60       bpm ( beats per minute used e.g. for HR/PULSE )
# NOM_PULS_OXIM_PERF_REL           10.0     - ( no dimension )

example_parsed = {
    "l": [
        {"n": "500A", "v": 15.0},
        {"n": "4182", "v": 60.0},
        {"n": "F0E5", "v": 60.0},
        {"n": "4A07", "v": 90.0},
        {"n": "4A06", "v": 80.0},
        {"n": "4A05", "v": 120.0},
    ],
    "n": "v",
    "v": "1681161101922",
}


def getdata_old(d, acc):
    # the datastructure is a nested dictionary
    # to extract the information we need to
    # recursively get the SCADAType fields
    # search each subkeys until everything up to these keys is found
    if type(d) == dict:
        v = d.get("SCADAType", [])
        if v[:3] == "NOM":
            acc += [d]
        else:
            for k in d:
                getdata_old(d[k], acc)


def getdata(d, acc):
    # print(d)
    RemoteOperationType = d.get("ROapdus", {"ro_type": "NONE"})["ro_type"]
    if (
        RemoteOperationType == "ROLRS_APDU"
    ):  # first and second, with seconds using RorlsId state of RORLS_LAST
        print("Recieved ROLRS")
        RemoteOperationLinkedResult = d.get(
            "ROLRSapdu", {"RolrsId": {"state": "NONE", "Rolrs_count": 0}}
        )
        # get state, get count, compile data
    elif RemoteOperationType == "RORS_APDU":  # last, remote op result message
        print("recieved RORS")
        # compile all the previous ROLRS data packets and send an MQTT packet here
        return  # RORS has no data
    elif RemoteOperationType == "NONE":
        print("Something other than RORS or ROLRS sent.")
        return
    else:
        print(f"Recieved ROapdus ro_type of {RemoteOperationType}")
        return
    # print(f"{RemoteOperationLinkedResult=}")
    # print("state=",RemoteOperationLinkedResult["RolrsId"]["state"])
    # print("count=",RemoteOperationLinkedResult["RolrsId"]["Rolrs_count"]) #is RORLS_LAST, RORLS_NOT_FIRST_NOT_LAST, RORLS_FIRST

    # parse_rols
    rolslist = []
    pollinfolist = d["PollMdibDataReplyExt"]["PollInfoList"]
    # print("pollinfolist=")
    # print(pollinfolist)

    singlecontexts = [
        pollinfolist[f"SingleContextPoll_{x}"]
        for x in range(int(pollinfolist["count"]))
    ]
    # print(f"\n\n{singlecontexts=}")
    for singlecontext in singlecontexts:
        pollinfo = singlecontext["SingleContextPoll"]["poll_info"]
        observations = [
            pollinfo[f"ObservationPoll_{x}"] for x in range(int(pollinfo["count"]))
        ]
        # print(observations)
        for observation in observations:
            count = int(observation["ObservationPoll"]["AttributeList"]["count"])
            attributelist = observation["ObservationPoll"]["AttributeList"]["AVAType"]
            for attribute in attributelist.keys():
                # print(attribute)
                if attribute == "NOM_ATTR_NU_VAL_OBS":
                    print(
                        "name=",
                        attributelist[attribute]["AttributeValue"]["NuObsValue"][
                            "SCADAType"
                        ],
                    )
                    print(
                        "data=",
                        attributelist[attribute]["AttributeValue"]["NuObsValue"][
                            "FLOATType"
                        ],
                    )
                    rolslist += [
                        attributelist[attribute]["AttributeValue"]["NuObsValue"]
                    ]
                if attribute == "NOM_ATTR_NU_CMPD_VAL_OBS":
                    compoundvalues = attributelist[attribute]["AttributeValue"][
                        "NuObsValCmp"
                    ]
                    values = [
                        compoundvalues[f"NuObsValue_{x}"]
                        for x in range(int(compoundvalues["count"]))
                    ]
                    # print(f"{values=}")
                    for val in values:
                        print("name=", val["NuObsValue"]["SCADAType"])
                        print("data=", val["NuObsValue"]["FLOATType"])
                        rolslist += [val["NuObsValue"]]
    print(f"{rolslist=}")
    # getdata_old(d,acc)#why does this crash on ETco2?
    acc += rolslist
    print(f"{acc=}")


def make_nv(data):
    # todo, potentially convert units
    # everything matched in demo mode
    n = desired_fields.get(data["SCADAType"], data["SCADAType"])
    v = data.get("FLOATType", "")
    return {"n": n, "v": v}


def process_data(d):
    acc = []
    getdata(d, acc)
    legacy = [make_nv(i) for i in acc]
    legacy = [i for i in legacy]  # if i["n"] in desired_fields.values()]
    l = dict([i["n"], i["v"]] for i in legacy)
    return l, legacy  # ~= example_parsed["l"]


if __name__ == "__main__":
    print(process_data(example_response))
