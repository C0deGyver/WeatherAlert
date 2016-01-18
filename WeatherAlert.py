#!/usr/bin/python3
#** this program is intended for use on a RaspberryPi
#**  it checks for weather 'alerts' through the internet according to the config file
# Copyright 2015 by David Daniluk (C0deGyver)
# GNU General Public License

import os.path
import configparser
try:
    import RPi.GPIO as GPIO
    from getpass import getuser
    rpi = True
except ImportError:
    from tkinter import *
    rpi = False
from time import strftime, sleep
from sys import exit
import subprocess
import threading
import urllib.request
import re

# notifyStops the program from being run with out root privileges for GPIO
if (rpi and getuser() != "root"):
    exit("Must be run as root or with sudo privileges.")

# program version string
programVersion = "6.1.1b"
# WARNING this program is in beta
#   looking for people willing to test my program

# setting up configparser to be config for program
config = configparser.ConfigParser(allow_no_value = True)
# adding a comment function to configparser
configparser.ConfigParser.add_comment = lambda self, section, option: self.set(section, '# '+option)

# vars to hold current results for notification process
global results

# var to notifyStop notification process
global notifyStop
global workerStop
workerStop = False
global wrapCutoff
global logCorrect
logCorrect = True

# checks to see if the pin in section is a board number
def checkBoardPins(section, pin, logLevel):
    if (pin == 11 or pin == 13 or pin == 15 or pin == 29 or pin == 31 or pin == 33 or pin == 35 or pin == 37 or pin == 12 or pin == 16 or pin == 18 or pin == 22 or pin == 32 or pin == 36 or pin == 37 or pin == 40):
        return True
    else:
        # if not a board number exits the program to prevent GPIO failure
        logString = section + " is not set to an acceptable board value."
        log(logLevel, 2, logString)
        exit("Config file not properly setup!")
        return False

# checks to see if the pin in section is a bcm number
def checkBcmPins(section, pin, logLevel):
    if (pin == 17 or pin == 27 or pin == 22 or pin == 5 or pin == 6 or pin == 13 or pin == 19 or pin == 26 or pin == 18 or pin == 23 or pin == 24 or pin == 25 or pin == 12 or pin == 16 or pin == 20 or pin == 21):
        return True
    else:
        # if not a board number exits the program to prevent GPIO failure
        logString = section + " is not set to an acceptable bcm value."
        log(logLevel, 2, logString)
        exit("Config file not properly setup!")
        return False

# tests string to see if in an integer containing from min size to max size digits and is unsigned
def intTest(testString, minSize, maxSize):
    try:
        int(testString)
        fail = True
        # checks the number of digits
        if not (len(testString) >= minSize and len(testString) <= maxSize):
            fail = False
        # checks to see if the number is negative
        if "-" in testString:
            fail = False
        return fail
    except ValueError:
        return False

# checks log level and logs appropriate amount of info
def log(logLevel, eventLevel, event):
    logFile = open('WeatherAlertLog.txt', 'a')
    date = strftime("%F @ %I:%M %p")
    eventString = date + " -- " + event + "\n"
    # checks to make sure logLevel is an integer
    if (intTest(logLevel, 1, 1)):
        # checks logLevel to see if it is 1, 2, 3, or 4
        if (logLevel == "1" or logLevel == "2" or logLevel == "3" or logLevel == "4"):
            logLevel = int(logLevel)
            # if log level is 2 and event level is 2 log it
            if (logLevel == 2 and eventLevel == 2):
                logFile.write(eventString)
            # if log level is 3 log all events 
            elif (logLevel == 3):
                logFile.write(eventString)
            # if log level is 4 print log instead of writing file (specifically for debugging)
            elif (logLevel == 4):
                print(event, "\n")
        # if logLevel is not 1, 2, or 3 exit program with error
        else:
            logFile.write("logLevel is not set to an acceptable value. Must be 1, 2, or 3.")
            exit("Config file not properly setup! Check the log.")
    # if logLevel is not an integer exit program with error
    else:
        logFile.write("logLevel is not set to an acceptable value. Must be an integer.")
        exit("Config file not properly setup! Check the log.")
    logFile.close()

# creates initial ini file for user
def writeAlertIni():
    file = open('WeatherAlert.ini', 'w')
    # writes main section to the file
    # I'm not using configparser here because
    #     it is easier to make pre-comments with the normal file.write() method
    file.write("# the main section should not be deleted\n\n")

    # writes main section of ini (program setup options)
    config.add_section("main")
    config.add_comment("main", "the current version number of the config file")
    config.set("main", "Version = " + programVersion + "\n")

    config.add_comment("main", "the log level for the program -- value can be: 1, 2, or 3")
    config.add_comment("main", "the 1 setting results in no logging.")
    config.add_comment("main", "the 2 setting results major error logging.")
    config.add_comment("main", "the 3 setting is the most logging, meant for error reporting.")
    config.set("main", "logLevel", "2\n")

    config.add_comment("main", "the amount of time the programs waits between weather checks -- value can be any number.")
    config.add_comment("main", "the setting of 0 will make the program run only once (intended for use when put in chrontab)")
    config.set("main", "waittime", "0\n")

    config.add_comment("main", "the pin numbering plan -- value can be: board or bcm")
    config.set("main", "boardnumberingplan", "board\n")

    config.add_comment("main", "the pin number used for the mute button -- value can be set to any valid pin number depending on board or bcm plan")
    config.set("main", "mutebuttonpin", "15\n")

    config.add_comment("main", "the action of the mute button -- value can be: read or mute")
    config.add_comment("main", "the read setting results in the pi muting the alert tone and reading aloud the warning that caused the alert")
    config.add_comment("main", "the mute setting results in muting the alert tone and no further action")
    config.set("main", "mutebuttonaction", "read\n")

    config.add_comment("main", "the ability to add an alarm output -- value can be: true or false")
    config.add_comment("main", "set this to true if you wish for the pi to output an alarm signal to a pin")
    config.set("main", "alarmoutput", "true\n")

    config.add_comment("main", "the pin used for the alarm output -- value can be set to any valid pin number depending on board or bcm plan")
    config.set("main", "alarmoutputpin", "22\n")

    config.add_comment("main", "the amount of time the alarm output pin is activated")
    config.set("main", "alarmoutputtime", "5\n")

    config.add_comment("main", "the amount of time between alert notices")
    config.set("main", "alertwait", "60\n\n")

    # writes examples to file
    config.add_comment("main", "###############  example alert Section  ############### #")
    config.add_comment("main", "one alert section will need to be created for individual states, zones\counties, and alertwatches as seen below")
    config.add_comment("main", "the alert watch is a greedy algorithm it will find any alerts with your word in them.")
    config.add_comment("main", "only use one code to select area being monitored either zone or county")

    config.add_section("example")
    config.add_comment("example", "state should be the two letter abbreviation for the state")
    config.set("example", "state", "ok\n")

    config.add_comment("example", "zone the zone code for the area you want monitored")
    config.add_comment("example", "if you wish to monitor the entire state do not include this")
    config.set("example", "zone", "001\n")

    config.add_comment("example", "county the county code for the area you want monitored")
    config.add_comment("example", "if you wish to monitor the entire state do not include this either")
    config.add_comment("example", "county = 025\n")

    config.add_comment("example", "alertwatch is the type of activity being monitored for")
    config.set("example", "alertwatch", "wind")

    config.add_section("example2")
    config.add_comment("example2", "state should be the two letter abbrevation for the state")
    config.set("example2", "state", "ok\n")

    config.add_comment("example2", "zone the zone code for the area you want monitored")
    config.add_comment("example2", "if you wish to monitor the entire state do not include this")
    config.add_comment("example2", "zone = 006\n")

    config.add_comment("example2", "county the county code for the area you want monitored")
    config.add_comment("example2", "if you wish to monitor the entire state do not include this either")
    config.set("example2", "county", "003\n")

    config.add_comment("example2","alertwatch is the type of activity being monitored for")
    config.set("example2", "alertwatch", "fire")

    config.write(file)
    file.close()

# reads the main section of the config
def readMainSection():
    global logCorrect
    # setting vars for future use
    file = open('WeatherAlert.ini', 'r')
    config.readfp(file)
    sections = config.sections()
    configVersion = config["main"].get("version")
    logLevel = config["main"].get("loglevel")
    waitTime = config["main"].get("waittime")
    boardNumberingPlan = config["main"].get("boardnumberingplan")
    muteButtonPin = config["main"].get("mutebuttonpin")
    muteButtonAction = config["main"].get("mutebuttonaction")
    alarmOutput = config["main"].get("alarmoutput")
    alarmOutputPin = config["main"].get("alarmoutputpin")
    alarmOutputTime = config["main"].get("alarmoutputtime")
    alertWait = config["main"].get("alertwait")
    log(logLevel, 3, "Config exists and is loaded.")

    # program primary, program secondary, program tertiary
    pp, ps, pt = programVersion.split('.')
    # config primary, config secondary, config tertiary
    cp, cs, ct = configVersion.split('.')

    # checks program version string against config version string for major updates
    #   if not then warns user and exits program
    if (pp != cp):
        logCorrect = False
        log("4", 2, "Config file not in current version major changes have happened. Please back up your file and allow the program to create a new example.")
        exit("Config file not in current version! Check the log.")

    # checks the waittine to make sure it is an integer
    if (intTest(waitTime, 1, 6)):
        waitTime = int(waitTime)
        logString = "waitTime is set to: " + str(waitTime)
        log(logLevel, 3, logString)
    # if not an integer exit program to prevent failure
    else:
        log(logLevel, 2, "waitTime is not set to an acceptable value. Must be a unsigned number.")
        exit("Config file not properly setup! Check the log.")

    # checks mute button pin to make sure it is an integer
    if (intTest(muteButtonPin, 1, 2)):
        logString = "muteButtonPin is set to: " + muteButtonPin
        log(logLevel, 3, logString)
        muteButtonPin = int(muteButtonPin)
    # if not an integer exit program to prevent failure
    else:
        log(logLevel, 2, "muteButtonPin is not set to an acceptable value. Must be a valid pin number.")
        exit("Config file not properly setup! Check the log.")

    # checks alarm output pin to make sure it is an integer
    if (intTest(alarmOutputPin, 1, 2)):
        logString = "alarmOutputPin is set to: " + alarmOutputPin
        log(logLevel, 3, logString)
        alarmOutputPin = int(alarmOutputPin)
    # if not an integer exit program to prevent failure
    else:
        log(logLevel, 2, "Alarmaoutputpin is not set to an acceptable value. Must be a valid pin number.")
        exit("Config file not properly setup! Check the log.")

    # checks alarm output for proper setup if not exit program with error
    if (alarmOutput == "true"):
        logString = "alarmOutput is set to: " + alarmOutput
        log(logLevel, 3, logString)
        alarmOutput = True
    elif (alarmOutput == "false"):
        logString = "alarmOutput is set to: " + alarmOutput
        log(logLevel, 3, logString)
        alarmOutput = False
    else:
        log(logLevel, 2, "alarmOutput is not set to an acceptable value. Must be either true or false.")
        exit("Config file not properly setup! Check the log.")

    # checks alarm output time to make sure it is an integer
    if  (intTest(alarmOutputTime, 1, 6)):
        logString = "alarmOutputTime is set to: " + alarmOutputTime
        log(logLevel, 3, logString)
        alarmOutputTime = int(alarmOutputTime)
    # if not an integer exit program to prevent failure
    else:
        log(logLevel, 2, "alarmOutputTime is not set to an acceptable value. Must be a unsigned number.")
        exit("Config file not properly setup! Check the log.")

    # checks alert wait to make sure it is an integer
    if  (intTest(alertWait, 1, 6)):
        logString = "alertWait is set to: " + alertWait
        log(logLevel, 3, logString)
        alertWait = int(alertWait)
    # if not an integer exit program to prevent failure
    else:
        log(logLevel, 2, "alertWait is not set to an acceptable value. Must be a unsigned number.")
        exit("Config file not properly setup! Check the log.")

    # checks to see if the pc is a rpi
    if rpi:
        log(logLevel, "3", "Rpi machine found using GPIO")

        # check for board numbering plan
        if (boardNumberingPlan == "board"):
            GPIO.setmode(GPIO.BOARD)
            logString = "boardNumberingPlan is set to: " + boardNumberingPlan
            log(logLevel, 3, logString)

            # setup mute button pin
            if (checkBoardPins("muteButtonPin", muteButtonPin, logLevel)):
                GPIO.setup(muteButtonPin, GPIO.IN)
                logString = "GPIO for mute set: " + str(muteButtonPin)
                log(logLevel, 3, logString)

            if (alarmOutput and checkBoardPins("alarmOutputPin", alarmOutputPin, logLevel)):
                GPIO.setup(alarmOutputPin, GPIO.OUT)
                logString = "GPIO for alarm output set: " + str(alarmOutputPin)
                log(logLevel, 3, logString)

        # check for bcm numbering plan
        elif (boardNumberingPlan == "bcm"):
            GPIO.setmode(GPIO.BCM)
            logString = "boardNumberingPlan is set to: " + boardNumberingPlan
            log(logLevel, 3, logString)

            # setup mute button pin
            if (checkBcmPins("muteButtonPin", muteButtonPin, logLevel)):
                GPIO.setup(muteButtonPin, GPIO.IN)
                logString = "GPIO for mute set: " + str(muteButtonPin)
                log(logLevel, 3, logString)

            if (alarmOutput and checkBcmPins("alarmOutputPin", alarmOutputPin, logLevel)):
                GPIO.setup(alarmOutputPin, GPIO.OUT)
                logString = "GPIO for alarm output set: " + str(alarmOutputPin)
                log(logLevel, 3, logString)
                    
        # if not board or bcm exit program with error
        else:
            log(logLevel, 2, "boardNumberingPlan is not set to an acceptable value. Must be either board or bcm.")
            exit("Config file not properly setup! Check the log.")

    # checks mute button action for proper setup if not exit program with error
    if not (muteButtonAction == "read" or muteButtonAction == "mute"):
        log(logLevel, 2, "muteButtonAction  is not set to an acceptable value. Must be wither read or mute.")
        exit("Config file not properly setup! Check the log.")
    else:
        logString = "muteButtonAction is set to: " + muteButtonAction
        log(logLevel, 3, logString)

    log(logLevel, 3, "Main section of config has been proccessed.")

    # closes the file
    file.close()

    # returns the vars to raise them out of local scope
    return (configVersion, logLevel, waitTime, boardNumberingPlan, muteButtonPin, muteButtonAction, alarmOutput, alarmOutputPin, alarmOutputTime, alertWait)

# replacement for linux grep command
def grep(string, pattern):
    temp = re.findall(r'^.*%s.*?$' % pattern, string, flags = re.M)
    # for true grep like results return "\n".join(re.findall(r'^.*%s.*?$' % pattern, string, flags = re.M))
    return temp[1]

# a function to handle notifications
def notify():
    # setting up vars
    global resulte
    global notifyStop
    notifyStop = False
    memory = []
    # transfer results to memory
    for r in range(len(results)):
        memory.append(results[r])

    while not notifyStop:
        try: 
            # if the mute button is pressed do appropriate action according to config
            if (GPIO.event_detected(muteButtonPin)):
                log(logLevel, 3, "Mute button pressed.")
                # mutes the alarm
                if (muteButtonAction == "mute"):
                    log(logLevel, 3, "Muted.")
                # runs through the relevant alerts and notifies user
                else:
                    for l in range(len(memory)):
                        logString = "Results #" + str(l) + ": '" + memory[l] + "' was alerted."
                        log(logLevel, 3, logString)
                        subprocess.call("espeak -s 120 --stdout " + "'" + memory[l] + "' | aplay -q", shell=True)
                memory = []
                notifyStop = True
            # notifies user as often as user has requested in config file
            else:
                log(logLevel, 3, "Alert detected... Notifing the user.")
                # turns the alarm output pin on/off
                if (alarmOutput):
                    GPIO.output(alarmOutputPin, 1)
                    sleep(alarmOutputTime)
                    GPIO.output(alarmOutputPin, 0)
                sleep(alertWait - alarmOutputTime)
        except KeyboardInterrupt:
            notifyStop = True

# a function that gets the alerts to be notified
def worker():
        # setting up vars
        global results
        global workerStop
        currentResults = []
        prevResults = []
        global wrapCutoff
        
        # loops endlessly to gather notifications
        while not workerStop:
            # checks to see if the pc is a rpi
            if rpi:
                # setting up thread for possible use
                notification = threading.Thread(target = notify, name = "worker")
            # setting vars for future use
            file = open('WeatherAlert.ini', 'r')
            config.readfp(file)
            sections = config.sections()
            results = []
            remove = []

            # removes the main section from the list so we can process user imputed sections
            sections.pop(0)

            # processes user imputed sections
            for i in range(len(sections)):
                # creates array of keys to process
                keys = list(config[sections[i]].keys())
                # check to make sure only zone or county is used in one key
                if (("zone" in keys) and ("county" in keys)):
                    # if both are used exit program with error
                    logString = "More than one parameter set in section: " + config.sections[i] + ". Only use zone OR county in one section."
                    log(logLevel, 2, logString)
                    exit("Config file not properly setup! Check the log.")
                else:
                    # if a key is a zone use zone rss address
                    if ("zone" in keys):
                        rssAddress = "http://alerts.weather.gov/cap/wwaatmget.php?x=" + config[sections[i]].get("state").upper() + "Z" + config[sections[i]].get("zone") + "&y=1"
                        logString = "User keyed section of config #" + str(i) + " Zone: " + config[sections[i]].get("state") + " " + config[sections[i]].get("zone") + " " + config[sections[i]].get("alertwatch")
                        log(logLevel, 3, logString)
                    # if a key is a county use county rss address
                    elif ("county" in keys):
                        rssAddress = "http://alerts.weather.gov/cap/wwaatmget.php?x=" + config[sections[i]].get("state").upper() + "C" + config[sections[i]].get("county") + "&y=1"
                        logString = "User keyed section of config #" + str(i) + " " + " County: " + config[sections[i]].get("state") + " " + config[sections[i]].get("county") + " " + config[sections[i]].get("alertwatch")
                        log(logLevel, 3, logString)
                    # if a key is a state use state rss address
                    else:
                        rssAddress = "http://alerts.weather.gov/cap/" + config[sections[i]].get("state") + ".php?x=1"
                        logString = "User keyed section of config #" + str(i) + " " + " State: " + config[sections[i]].get("state") + " " + config[sections[i]].get("alertwatch")
                        log(logLevel, 3, logString)
                    # use request to obtain all alerts in the requested areas
                    indResults = urllib.request.urlopen(rssAddress)
                    # decodes into human readable
                    indResults = indResults.read().decode('utf-8')
                    # searches text for alerts and do some replacements
                    indResults = grep(indResults, "<title>").lower().replace("<title>", "").replace("nws", "national weather service").replace("cdt", "").replace("mst", "")
                    # split the results into an array for processing later
                    indResults = indResults.split("</title>")
                    # creates one array containing all relevant alerts
                    if (config[sections[i]].get("alertwatch") in indResults[0]):
                        results.append(indResults[0])
                        currentResults.append(indResults[0])

            # stages the removal of already notified alerts
            for a in range(len(results)):
                for b in range(len(prevResults)):
                    if (results[a] == prevResults[b]):
                        remove.append(results[a])
            # removes staged alerts
            for c in range(len(remove)):
                results.remove(remove[c])

            # notifyStops alert thread if the alerts are no longer there
            if (len(results) == 0):
                notifyStop = True
                if not rpi:
					# hids the tk window
                    root.withdraw()

            # processes the alerts if they exist
            if (len(results) > 0):
                notifyStop = False
                # checks to see if the pc is a rpi
                if rpi:
                    # starts notification process
                    notification.start()
                    if waitTime == 0:
                        notification.join()
                else:
					# captures previous notification(s)
                    delete = alertFrame.winfo_children()
					# deletes labels for previous notification(s)
                    for d in alertFrame.winfo_children():
                        d.pack_forget()
					# adds labels for current notification(s)
                    for l in range(len(results)):
						# logs the notification(s)
                        logString = "Results #" + str(l) + ": '" + results[l] + "' was alerted."
                        log(logLevel, 3, logString)
                        label = Label(alertFrame, wraplength = wrapCutoff, justify = LEFT, text=results[l])
                        label.pack(side = TOP, expand = 1, fill = X)
					# forces the alert frame to refresh
                    alertFrame.update_idletasks()
					# un-hides the tk window
                    root.deiconify()        

                # sets prevResults to results to prevent warning more than once about the same alert
                prevResults = currentResults
            # if already reported logs nothing to report
            else:
                log(logLevel, 3, "All results have been alerted already.")
            # resets current results
            currentResults = []
            # waits the amount of time the user specified
            if (waitTime > 0):
                logString = "Waiting " + str(waitTime) + " seconds until next run."
                log(logLevel, 3, logString)
                sleep(waitTime)
            else:
				# breaks the loop
                workerStop = True

# resets alert canvas
def onFrameConfigure(alertCanvas):
    alertCanvas.configure(scrollregion=alertCanvas.bbox("all"))

# resizes the wrap length of alert labels
def onResize(event, alertCanvas):
    for l in alertCanvas.winfo_children():
        l.configure(wraplength = event.width - 20)

# hides tk window
def alertsRead(root):
    if (waitTime > 0):
        root.withdraw()
    else:
        root.destroy()
    
# checks for keyboard interrupt
def checkInterrupt(root):
    try:
        root.after(1, checkInterrupt, root)
    except KeyboardInterrupt:
        root.destroy()

# setup for Keyboard Interrupt
try:
    # check if config exists
    configExists = os.path.isfile('WeatherAlert.ini')
    global wrapCutoff

    # if true read all of the main settings in
    # and run the normal program
    if (configExists):
        # setting vars for future use
        configVersion, logLevel, waitTime, boardNumberingPlan, muteButtonPin, muteButtonAction, alarmOutput, alarmOutputPin, alarmOutputTime, alertWait = readMainSection()
        # checks to see if the pc is a rpi
        if rpi:
            # adds event detection for mute button
            GPIO.add_event_detect(muteButtonPin, GPIO.RISING)
            # calls function to get alerts
            worker()
        else:
			# logs nonRpi os
            log(logLevel, "3", "nonRpi os detected")
			# starts worker in background / another thread
            working = threading.Thread(target = worker)
            working.start()
			# makes tk window to show alerts
            root = Tk()
            root.title("Weather Alerts")

            # setting up window geometry
            startWidth = (root.winfo_screenwidth() / 3)
            startHeight = (root.winfo_screenheight() / 3)
            root.wm_geometry("%dx%d+%d+%d" % (startWidth, startHeight, 0, 0 ))

            # frames for holding all widgets
            topFrame = Frame(root)
            topFrame.pack(side = TOP, expand = 1, fill = BOTH)
            bottomFrame = Frame(root)
            bottomFrame.pack(side = BOTTOM, expand = 0, fill = X)

            # alert containers
            alertCanvas = Canvas(topFrame)
            alertCanvas.pack(side = LEFT, expand = 1, fill = BOTH)
            alertFrame = Frame(alertCanvas)
            alertFrame.pack(side = TOP, expand = 1, fill = BOTH)
            alertFrame.bind("<Configure>", lambda event, alertCanvas = alertCanvas: onFrameConfigure(alertCanvas))
            topFrame.bind("<Configure>", lambda event, alertFrame = alertFrame: onResize(event, alertFrame))

            # scrollbar
            scrollbar = Scrollbar(topFrame, orient="vertical", command=alertCanvas.yview)
            scrollbar.pack(side = LEFT, fill = Y)
            alertCanvas.configure(yscrollcommand = scrollbar.set)
            alertCanvas.create_window((0,0), window = alertFrame, anchor = "nw")

            # okay button to close window
            button = Button(bottomFrame, text='Okay', command = lambda: alertsRead(root))
            button.pack(side = TOP, fill = X)

            # cut off for label text
            wrapCutoff = startWidth - 20

            root.after(1, checkInterrupt, root)
            root.withdraw()
            root.mainloop()

    # if config is missing creates one
    else:
        log("4", 2, "The config file is missing... Creating one.")
        writeAlertIni()
        exit("No config file... Creating one for you.")

# pressing ctrl+c will close the program
except KeyboardInterrupt:
    # log keyboard interrupt
    if not configExists:
        log("4", 2, "\nKeyboard interrupt has been activated.")
    else:
        log(logLevel, 2, "\nKeyboard interrupt has been activated.")
    # terminate notification thread safely
    if (threading.active_count() > 1):
        if rpi:
            notifyStop = True
        else:
            workerStop = True
            root.destroy()

        # log thread notifyStop
        if not configExists:
            log("4", 2, "Stopping notification.")
        else:
            log(logLevel, 2, "Stopping notification.")

finally:
    # wait for notification thread to terminate safely
    if (threading.active_count() > 1):
        while threading.active_count() > 1:
            sleep(0.25)

    # program not on first run needs to clean up GPIO
    if (rpi and configExists):
        GPIO.remove_event_detect(muteButtonPin)
        sleep(1)
        GPIO.cleanup()

        # log gpio clean up
        log(logLevel, 2, "GPIO cleaned up.")

    # destroys tk's loop
    if (not rpi and configExists and threading.active_count() > 1):
        root.destroy()

    #log program shutting down    
    if not configExists:
        log("4", 2, "Program shutting down.")
    elif not (logCorrect):
        log("4", 2, "Program shutting down.")
    else:
        log(logLevel, 2, "Program shutting down.")
    exit(0)
