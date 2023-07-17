nterfaces=[]
for x in str(subprocess.check_output("sudo dmesg |grep -e ttyAMA[1-4]",shell=True))[2:-3].split("\\n"):
        try:
                    index=x.find("tty")
                            tty=x[index:index+8].strip(" ")
                                    interfaces.append(tty)
                                        except:
                                                    print("nothing found")

