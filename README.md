# WeatherAlert
This program was originally written specifically for the RaspberryPi
Also it is currently beta... which means there might be issues

General Info:
    The first run of the program will create a sample config file for you: WeatherAlert.ini
        This first run will self terminate after the file has been created

    Since GPIO functions do not work so well without root privileges.. 
    You will need to run the program by: sudo python3 WeatherAlert.py
    This means the log file and config file have root ownership
    I would personally recommend changing the ownership of these to your user by:
        sudo chown user:user WeatherAlert.log && sudo chown user:user WeatherAlert.ini
