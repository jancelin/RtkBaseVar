import io
import serial
import pynmea2
import time
import subprocess
import os
import signal
import telegram
import telebot
from telebot import types
import sys
from decimal import *
from ntripbrowser import NtripBrowser
import multiprocessing
from datetime import datetime
import config
import configparser

##global varible loops
loop_str = None

## import and edit .ini
configp = configparser.ConfigParser()
configp.read('param.ini')

def editparam():
    with open('param.ini','w') as configfile:
        configp.write(configfile)

##TElegram param
config.api_key = str( sys.argv[1] )
config.user_id = str( sys.argv[2] )
bot = telebot.TeleBot(config.api_key)

@bot.message_handler(commands=['restart'])
def send_restart(message):
    configp.read('param.ini')
    bot.reply_to(message, 'Restarting SERVICE......')
    restartbasevar()

#base filter
@bot.message_handler(commands=['excl'])
def send_exclE(message):
    configp.read('param.ini')
    msg = bot.reply_to(message,"Edit exclude Base(s):\n old value:"+configp["data"]["exc_mp"]+",\n Enter the new value ! ")
    bot.register_next_step_handler(msg, processSetExclE)
def processSetExclE(message):
    answer = message.text
    if answer.isupper():
        print(answer)
        configp["data"]["exc_mp"] = answer
        stoptowrite()
        bot.reply_to(message,"NEW exclude Base(s): "+configp["data"]["exc_mp"])
    else:
        bot.reply_to(message, 'Oooops bad value!')


#hysteresis
@bot.message_handler(commands=['htrs'])
def send_htrsE(message):
    configp.read('param.ini')
    msg = bot.reply_to(message,"Edit Hysteresis:\n old value:"+configp["data"]["htrs"]+"km,\n Enter the new value ! ")
    bot.register_next_step_handler(msg, processSetHtrsE)
def processSetHtrsE(message):
    answer = message.text
    if answer.isdigit():
        print(answer)
        configp["data"]["htrs"] = answer
        stoptowrite()
        bot.reply_to(message,"NEW Hysteresis: "+configp["data"]["htrs"]+"km")
    else:
        bot.reply_to(message, 'Oooops bad value!')

#Critical distance
@bot.message_handler(commands=['crit'])
def send_critE(message):
    configp.read('param.ini')
    msg = bot.reply_to(message,"Edit Maximum distance before GNSS base change:\n Old value:"+configp["data"]["mp_km_crit"]+"km,\n Enter the new value ! ")
    bot.register_next_step_handler(msg, processSetCritE)
def processSetCritE(message):
    answer = message.text
    if answer.isdigit():
        print(answer)
        configp["data"]["mp_km_crit"] = answer
        stoptowrite()
        bot.reply_to(message,"NEW Maximum distance before GNSS base change saved: "+configp["data"]["mp_km_crit"]+"km")
    else:
        bot.reply_to(message, 'Oooops bad value!')

#Critical distance
@bot.message_handler(commands=['dist'])
def send_distE(message):
    configp.read('param.ini')
    msg = bot.reply_to(message,"Edit Max search distance of GNSS bases saved:\n old value:"+configp["data"]["maxdist"]+"km,\n Enter the new value ! ")
    bot.register_next_step_handler(msg, processSetDistE)
def processSetDistE(message):
    answer = message.text
    if answer.isdigit():
        print(answer)
        configp["data"]["maxdist"] = answer
        stoptowrite()
        bot.reply_to(message,"NEW Critical distance: "+configp["data"]["maxdist"]+"km")
    else:
        bot.reply_to(message, 'Oooops bad value!')

#dowload logs
@bot.message_handler(commands=['log'])
def notas(mensagem):
    mensagemID = mensagem.chat.id
    doc = open('basevarlog.csv', 'rb')
    bot.send_document(mensagemID, doc)

#principal messsage
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    configp.read('param.ini')
    mes=("Connected to Mount Point: \n*"+configp["data"]["mp_use"]+ "*\n" +
    "Last distance between Rover/Base: \n*"+configp["data"]["dist_r2mp"]+"*km" + "\n\n" + "Parameters:\n"
    "*/excl* Bases GNSS exclude: *"+configp["data"]["exc_mp"]+ "*\n" +
    "*/dist* Max search distance of bases: *"+configp["data"]["maxdist"]+"*km"+ "\n" +
    "*/crit* Maximum distance before base change: *"+ configp["data"]["mp_km_crit"] +"*km" + "\n" +
    "*/htrs* Hysteresis: *"+configp["data"]["htrs"]+"*km"+ "\n\n" +
    "*/log*  Download GNSS base change logs")
    bot.reply_to(message,mes,parse_mode= 'Markdown')

#Automatic message on base change with pytelegrambot (BUG with telebot)
def telegrambot():
    global bot1
    if len(sys.argv) >= 2:
        bot1 = telegram.Bot(token=config.api_key)
        bot1.send_message(chat_id=config.user_id, text=configp["message"]["message"])

def telegrambot2():
    global bot2
    if len(sys.argv) >= 2:
        bot2 = telegram.Bot(token=config.api_key)
        bot2.send_message(chat_id=config.user_id, text=configp["message"]["message2"])

def savelog():
    ##log in file
    file = open("basevarlog.csv", "a")
    file.write(configp["message"]["message"] +'\n')
    file.close

def movetobase():
    ## Build new str2str_in command
    bashstr = config.stream1 + mp_use1 + config.stream2
    ## LOG Move to base
    print("------")
    print("CASTER: Move to base ",mp_use1, " !")
    print("------")
    ## KILL old str2str_in
    killstr()
    ## Upd variables & Running a new str2str_in service
    configp["data"]["mp_use"] = mp_use1
    editparam()
    time.sleep(2)
    start_in_str2str()
    ##Metadata
    presentday = datetime.now()
    configp["message"]["message"] = ("Move to base ," + str(mp_use1) +","+
    str(round(mp_use1_km,2))+","+str(round(config.rlat,7))+","+
    str(round(config.rlon,7))+","+ presentday.strftime('%Y-%m-%d') +" "+str(config.rtime))
    editparam()
    telegrambot()

def ntripbrowser():
    global browser
    global getmp
    global flt1
    global mp_use1
    global mp_use1_km
    global mp_Carrier
    ## 2-Get caster sourcetable
    browser = (NtripBrowser(config.caster, port=config.port,
    timeout=10,coordinates=(config.rlat,config.rlon),
    maxdist=int(configp["data"]["maxdist"]) ))
    getmp= browser.get_mountpoints()
    flt = getmp['str']
    # Purge list
    flt1 = []
    ## Param base filter
    excl =  list(configp["data"]["exc_mp"].split(" "))
    ## filter carrier L1-L2 & exclude base
    flt1 = [m for m in flt if int(m['Carrier'])>=2 and m['Mountpoint'] not in excl]
    ## GET nearest mountpoint
    for i, value in enumerate(flt1):
        ## Get first row
        if i == 0 :
            ## LOG Nearest base available
            mp_use1 = value["Mountpoint"]
            mp_use1_km = value["Distance"]
            mp_Carrier = value["Carrier"]
            print(
                "INFO: Nearest base is ",mp_use1,
                round(mp_use1_km,2),"km; Carrier:",mp_Carrier)
            print(
                "INFO: Distance between Rover & connected base ",
                configp["data"]["mp_use"],Decimal(configp["data"]["dist_r2mp"]),"km")

    ## Value on connected base
    flt_r2mp = [m for m in flt if m['Mountpoint']==configp["data"]["mp_use"]]
    ## GET distance between rover and mountpoint used.
    for r in flt_r2mp:
        configp["data"]["dist_r2mp"] = str(round(r["Distance"],2))
        configp["data"]["mp_alive"] = r['Mountpoint']
        editparam()
    ## LOG Watch all nearests mountpoints
    # for i in flt:
    #     mp = i["Mountpoint"]
    #     di = round(i["Distance"],2)
    #     car = i["Carrier"]
    #     print(mp,di,"km; Carrier:", car)

## 03-START loop to check base alive + rover position and nearest base
def loop_mp():
    while True:
        try:
            global mp_use1
            global mp_use1_km
            global msg
            ##get variables
            configp.read('param.ini')
            ##Get data from Caster
            ntripbrowser()
            ##My base is Alive?
            flt_basealive = [m for m in flt1 if m['Mountpoint']==configp["data"]["mp_alive"]]
            if len(flt_basealive) == 0:
                print("INFO: Base ",configp["data"]["mp_alive"]," is DEAD!")
                movetobase()
                savelog()
            else:
                print("INFO: Connected to ",configp["data"]["mp_use"],", Waiting for the rover's geographical coordinates......")
                ## 1-Analyse nmea from gnss ntripclient for get lon lat
                ##TODO after x min reset parameters
                line = config.sio.readline()
                msg = pynmea2.parse(line)
                ## Exclude bad longitude
                if msg.longitude != config.lon:
                    ## LOG coordinate from Rover
                    config.rlat = msg.latitude
                    config.rlon = msg.longitude
                    config.rtime = msg.timestamp
                    print("------")
                    print("ROVER: ",config.rlat,config.rlon,msg.timestamp)
                    print("------")
                    ## 2-Get caster sourcetable
                    ntripbrowser()
                    ### Check if it is necessary to change the base
                    ## nearest Base is different?
                    if configp["data"]["mp_use"] != mp_use1:
                        ## Check Critical distance before change ?
                        if Decimal(configp["data"]["dist_r2mp"]) > int(configp["data"]["mp_km_crit"]):
                            ##critique + Hysteresis(htrs)
                            crithtrs = int(configp["data"]["mp_km_crit"]) + int(configp["data"]["htrs"])
                            if Decimal(configp["data"]["dist_r2mp"]) < crithtrs:
                                print("**INFO: Hysteresis critique running: ",crithtrs,"km")
                            else:
                                ##middle mount point 2 mount point hysteresis
                                r2mphtrs = mp_use1_km + int(configp["data"]["htrs"])
                                if Decimal(configp["data"]["dist_r2mp"]) < r2mphtrs:
                                    print("**INFO: Hysteresis MP 2 MP running: ",r2mphtrs,"km")
                                else:
                                    movetobase()
                                    savelog()
                        else:
                            print(
                                "**INFO:",mp_use1," nearby: ",Decimal(configp["data"]["dist_r2mp"]),
                                " But critical distance not reached: ",configp["data"]["mp_km_crit"],"km")
                    if configp["data"]["mp_use"] == mp_use1:
                        print("**INFO: Always connected to ",mp_use1)

        except serial.SerialException as e:
            #print('Device error: {}'.format(e))
            continue
        except pynmea2.ParseError as e:
            #print('Parse error: {}'.format(e))
            continue

## stop loop for change parameters (.ini)
def stoptowrite():
    global loop_str
    loop_str.terminate()
    time.sleep(2)
    editparam()
    loop_str = multiprocessing.Process(name='loop',target=loop_mp)
    loop_str.deamon = True
    print("Loop_str Starting:", multiprocessing.current_process().name)
    loop_str.start()

def restartbasevar():
        print("argv was",sys.argv)
        print("sys.executable was", sys.executable)
        print("restart now")
        ## KILL old str2str_in
        killstr()
        os.execv(sys.executable, ['python'] + sys.argv)

def killstr():
    # iterating through each instance of the process
    for line in os.popen("ps ax | grep 'str2str -in ntrip' | grep -v grep"):
        fields = line.split()
        # extracting Process ID from the output
        pidkill = fields[0]
        # terminating process
        os.kill(int(pidkill), signal.SIGKILL)
    print("KILLING all 'STR2STR -in ntrip' Successfully terminated")

## 00-START socat
## TODO : Open virtual ports, BUG don't run in background, use run.sh.
# def socat():
#  process1 = subprocess.Popen(config.socat.split())
#  print("/dev/pts/1 & /2 created")
#  time.sleep(3)

def str2str_out():
    global str2str_out
    ##run ntripcaster
    str2str_out = subprocess.Popen(config.ntripc.split())

def str2str_in():
    global str2str_in
    configp.read('param.ini')
    bashstr = config.stream1+configp["data"]["mp_use"]+config.stream2
    str2str_in = subprocess.Popen(bashstr.split())

def start_out_str2str():
    global out_str
    out_str = multiprocessing.Process(name='str_out',target=str2str_out)
    out_str.deamon = True
    print("Out_str Started:", multiprocessing.current_process().name)
    out_str.start()

def start_in_str2str():
    global in_str
    in_str = multiprocessing.Process(name='str_in',target=str2str_in)
    in_str.deamon = True
    print("In_str Started:", multiprocessing.current_process().name)
    in_str.start()

def start_loop_basevar():
    global loop_str
    loop_str = multiprocessing.Process(name='loop',target=loop_mp)
    loop_str.deamon = True
    print("Loop_str Starting:", multiprocessing.current_process().name)
    loop_str.start()

def main():
    telegrambot2()
    ##TODO socat
    start_out_str2str()
    start_in_str2str()
    start_loop_basevar()
    bot.infinity_polling()

    out_str.join()
    in_str.join()
    loop_str.join()

if __name__ == '__main__':
    main()
