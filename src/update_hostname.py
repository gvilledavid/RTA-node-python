from pulse.pulse import pulse
puls=pulse()
puls.update()
hostname=puls.get_hostname()
print(f"Hostname is {puls.get_hostname()}")
networks=puls.rawpulse["networking"]
macs=[]
for network in networks:
    macs.append(network['mac'].lower())
print(macs)
print(f"Networks are {networks}")
with open("hostnames.csv","r") as hostnames_file:
    header=hostnames_file.readline().replace("\n","").split(",")
    if "eth0" in header:
        eth_index=header.index("eth0")
    if "wlan0" in header:
        wlan_index=header.index("wlan0")       
    #devices=[]
    prescribed_hostname=""
    while True:
        line=hostnames_file.readline()
        if not line:
            break
        #device={}
        #for id,param in enumerate(line.replace("\n","").split(",")):
        #    device[header[id]]=param
        #devices.append(device)
        row=line.replace("\n","").split(",")
        #print(f"{row[0]} {row[eth_index]} {row[wlan_index]}")
        if(row[eth_index].lower() in macs or row[wlan_index].lower() in macs ):
            prescribed_hostname=row[0]
            break
if prescribed_hostname:
    print(f"Prescribed hostname is {prescribed_hostname}")
    if(hostname== prescribed_hostname):
        print("Hostname is correct!")
    else:
        print("Setting hostname now, root is required:")
        puls.set_hostname(prescribed_hostname)
        print(f"Read hostname: {puls.get_hostname()}")
else:
    print("name not found on list")
    
#print(f"All devices {devices}")
