 #!/usr/bin/env python
from PIL import Image, ImageOps
from PIL import ImageFont
from PIL import ImageDraw
import subprocess
import os
import sys
import logging
import traceback
import RPi.GPIO as GPIO
from waveshare_epd import epd2in7
import time
import requests
import urllib, json
import matplotlib.pyplot as plt
import numpy as np
import yaml 
import socket

def internet(host="8.8.8.8", port=53, timeout=3):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        print(ex)
        return False

def hideDisplay(config):
    """
    Hides everything but the date until a button is pressed. Currently of limited use. 
    """
    font_date = ImageFont.truetype('fonts/PixelSplitter-Bold.ttf',11)
    epd = epd2in7.EPD()
    epd.Init_4Gray()
    if config['display']['orientation'] == 0 or config['display']['orientation'] == 180 :
        epd = epd2in7.EPD()
        epd.Init_4Gray()
        image = Image.new('L', (epd.width, epd.height), 255)    # 255: clear the image with white
        draw = ImageDraw.Draw(image)              
        draw.text((0,10),str(time.strftime("%c")),font =font_date,fill = 0)
        if config['display']['orientation'] == 180 :
            image=image.rotate(180, expand=True)


    if config['display']['orientation'] == 90 or config['display']['orientation'] == 270 :
        epd = epd2in7.EPD()
        epd.Init_4Gray()
        image = Image.new('L', (epd.height, epd.width), 255)    # 255: clear the image with white
        draw = ImageDraw.Draw(image)   
        draw.text((85,5),str(time.strftime("%c")),font =font_date,fill = 0)
        if config['display']['orientation'] == 270 :
            image=image.rotate(180, expand=True)
#       This is a hack to deal with the mirroring that goes on in 4Gray Horizontal
        image = ImageOps.mirror(image)
    epd.display_4Gray(epd.getbuffer_4Gray(image))
    epd.sleep()    


def updateDisplay(config):
    """
    The function to update the ePaper display. There are two versions of the layout. One for portrait aspect ratio, one for landscape.
    """
    logging.info("Updating Display")   
    logging.info("Getting Data From CoinAPI")
    font = ImageFont.truetype('fonts/googlefonts/Roboto-Medium.ttf', 40)    
    fontHorizontal = ImageFont.truetype('fonts/googlefonts/Roboto-Medium.ttf', 50)
    font_date = ImageFont.truetype('fonts/PixelSplitter-Bold.ttf',11)
    now_msec_from_epoch = int(round(time.time() * 1000))
    days_ago = 7
    endtime = now_msec_from_epoch
    starttime = endtime - 1000*60*60*24*days_ago
    coinapi = "https://api.coincap.io/v2/assets/bitcoin/history?interval=h1&start="+str(starttime)+"&end="+str(endtime)
    rawtimeseries = requests.get(coinapi).json()
    logging.info("Got Historic Data For Last Week")
    timeseriesarray = rawtimeseries['data']
    timeseriesstack = []
    length=len (timeseriesarray)
    i=0
    while i < length:
        timeseriesstack.append(float (timeseriesarray[i]['priceUsd']))
        i+=1

    # Get the live price from coinapi
    livecoinapi= "https://api.coincap.io/v2/assets/bitcoin/"
    rawlivecoin = requests.get(livecoinapi).json()
    logging.info("Got Live Data")
    liveprice= rawlivecoin['data']
    
    BTC = float(liveprice['priceUsd'])

    # Add live price to timeseriesstack
    timeseriesstack.append(BTC)

    # Subtract the mean from the sparkline to make the mean appear on the plot (it's really the x axis)    
    x = timeseriesstack-np.mean(timeseriesstack)

    fig, ax = plt.subplots(1,1,figsize=(10,3))
    plt.plot(x, color='k', linewidth=6)
    plt.plot(len(x)-1, x[-1], color='r', marker='o')

    # Remove the Y axis
    for k,v in ax.spines.items():
        v.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axhline(c='k', linewidth=4, linestyle=(0, (5, 2, 1, 2)))

    # Save the resulting bmp file to the images directory
    plt.savefig('images/spark.png', dpi=17)
    imgspk = Image.open('images/spark.png')
    file_out = "images/spark.bmp"
    imgspk.save(file_out) 

    bmp = Image.open('images/BTC.bmp')
    bmp2 = Image.open('images/spark.bmp')


    if config['display']['orientation'] == 0 or config['display']['orientation'] == 180 :
        epd = epd2in7.EPD()
        epd.Init_4Gray()
        image = Image.new('L', (epd.width, epd.height), 255)    # 255: clear the image with white
        draw = ImageDraw.Draw(image)              
        draw.text((110,80),"7day :",font =font_date,fill = 0)
        draw.text((110,95),str("%+d" % round((timeseriesstack[-1]-timeseriesstack[1])/timeseriesstack[-1]*100,2))+"%",font =font_date,fill = 0)
        draw.text((5,200),"$"+format(int(round(BTC)),","),font =font,fill = 0)
        draw.text((0,10),str(time.strftime("%c")),font =font_date,fill = 0)
        image.paste(bmp, (10,20))
        image.paste(bmp2,(10,125))
        if config['display']['orientation'] == 180 :
            image=image.rotate(180, expand=True)


    if config['display']['orientation'] == 90 or config['display']['orientation'] == 270 :
        epd = epd2in7.EPD()
        epd.Init_4Gray()
        image = Image.new('L', (epd.height, epd.width), 255)    # 255: clear the image with white
        draw = ImageDraw.Draw(image)   
        draw.text((100,100),"7day : "+str("%+d" % round((timeseriesstack[-1]-timeseriesstack[1])/timeseriesstack[-1]*100,2))+"%",font =font_date,fill = 0)
        draw.text((20,120),"$"+format(int(round(BTC)),","),font =fontHorizontal,fill = 0)
        image.paste(bmp2,(80,50))
        image.paste(bmp, (0,0))
        draw.text((85,5),str(time.strftime("%c")),font =font_date,fill = 0)
        if config['display']['orientation'] == 270 :
            image=image.rotate(180, expand=True)
#       This is a hack to deal with the mirroring that goes on in 4Gray Horizontal
        image = ImageOps.mirror(image)

#   If the display is inverted, invert the image usinng ImageOps        
    if config['display']['inverted'] == True:
        image = ImageOps.invert(image)
#   Send the image to the screen        
    epd.display_4Gray(epd.getbuffer_4Gray(image))
    epd.sleep()

def main():
    logging.basicConfig(level=logging.DEBUG)

    try:
        logging.info("epd2in7 BTC Frame")
#       Get the configuration from config.yaml
        with open('config.yaml') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        logging.info(config)
        GPIO.setmode(GPIO.BCM)
        config['display']['orientation']=int(config['display']['orientation'])

        key1 = 5
        key2 = 6
        key3 = 13
        key4 = 19

        GPIO.setup(key1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(key2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(key3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(key4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
     
        updateDisplay(config)
        lastpresscoin=1
        lastcoinfetch = time.time()
        while True:
            key1state = GPIO.input(key1)
            key2state = GPIO.input(key2)
            key3state = GPIO.input(key3)
            key4state = GPIO.input(key4)

            if internet():
                if key1state == False:
                    logging.info('Force Refresh')
                    updateDisplay(config)
                    time.sleep(0.2)
                    laspresscoin=1
                if key2state == False:
                    logging.info('ROTATE90')
                    config['display']['orientation'] = (config['display']['orientation']+90) % 360
                    time.sleep(0.2)
                    updateDisplay(config)
                    with open('config.yaml', 'w') as f:
                       data = yaml.dump(config, f)
                    lastpresscoin=1
                if key3state == False:
                    logging.info('INVERT')
                    if config['display']['inverted'] == True:
                       config['display']['inverted'] = False
                    else:
                       config['display']['inverted'] = True 
                    updateDisplay(config)
                    with open('config.yaml', 'w') as f:
                       data = yaml.dump(config, f)

                    lastpresscoin=1
                    lastcoinfetch=time.time() 
                    time.sleep(0.2)
                if key4state == False:
                    logging.info('HIDE')
                    if config['ticker']['hidden'] == True:
                        config['ticker']['hidden'] = False
                        updateDisplay(config)
                    else:
                        config['ticker']['hidden'] = True 
                        hideDisplay(config)
                    time.sleep(0.2)
                    lastpresscoin=0
                if lastpresscoin==1:
                    if time.time() - lastcoinfetch > float(config['ticker']['updatefrequency']):
                        updateDisplay(config)
                        lastcoinfetch=time.time()
                        time.sleep(0.2)
            else:
                logging.info("No Internet")


    except IOError as e:
        logging.info(e)
    
    except KeyboardInterrupt:    
        logging.info("ctrl + c:")
        epd2in7.epdconfig.module_exit()
        exit()

if __name__ == '__main__':
    main()
