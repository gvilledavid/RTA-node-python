import serial
buffer=[]
string=b'MISCF,1225,169 ,\x0210:40 ,980 35B1500404    ,APR 24 2023 ,INVASIVE ,SIMV  ,VC    ,PS    ,V-Trig,15.0  ,0.245 ,27.0  ,40    ,      ,5.0   ,0.0   ,20    ,0.365 ,10.0  ,53.0  ,100   ,      ,      ,RAMP  ,VC    ,      ,      ,10    ,SQUARE,OFF   ,47    ,      ,18.500,2.500 ,480   ,150   ,480   ,255   ,OFF   ,      ,3.5   ,2.0   ,      ,      ,      ,      ,         ,      ,      ,HME               ,      ,Disabled ,75    ,70    ,      ,25.0  ,61.0  ,      ,      ,      ,      ,      ,ADULT    ,      ,      ,16.0  ,15.0  ,0.252 ,3.780 ,16.0  ,6.4   ,6.40  ,1:6.40,      ,0.115 ,      ,      ,      ,      ,      ,      ,      ,      ,5.0   ,0.35  ,0.00  ,0.0   ,0.0   ,28.0  ,4.8   ,14.0  ,      ,28.0  ,4.9   ,26.0  ,42.0  ,0.0   ,      ,0.0   ,0.0   ,0.000 ,OFF   ,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,RESET ,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,      ,      ,      ,      ,      ,      ,      ,      ,0.045 ,      ,OFF   ,      ,      ,      ,NORMAL,      ,      ,0.400 ,1.900 ,      ,      ,      ,      ,      ,      ,      ,BREATH,      ,\x03\r'



def get_ventilator_data(tty, brate, tout, cmd):
    with serial.Serial(tty, brate, timeout=tout,
            parity=serial.PARITY_NONE, rtscts=1) as ser:
        ser.flush()
        ser.write(cmd)
        line = ser.readline()
        # print( line )
        ser.close()
        return line
with serial.Serial("/dev/ttyUSB0",38400,parity=serial.PARITY_NONE,rtscts=1) as ser:
...      ser.flush()
...      ser.write(b'test')
...      line=ser.readline()
...      ser.close()
if __name__ == "__main__":
    print("raw_output = ", get_ventilator_data('/dev/ttyUSB0', 38400, 0.1, b'SNDF\r'))
