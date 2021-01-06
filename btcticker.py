#!/usr/bin/python3
from PIL import Image, ImageOps
from PIL import ImageFont
from PIL import ImageDraw
import currency
import os
import sys
import logging
import RPi.GPIO as GPIO
from waveshare_epd import epd2in7
import time
import requests
import urllib, json
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import yaml 
import socket
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')
fontdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fonts')
configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)),'config.yaml')
fonthiddenprice = ImageFont.truetype(os.path.join(fontdir,'googlefonts/Roboto-Medium.ttf'), 30)
font = ImageFont.truetype(os.path.join(fontdir,'googlefonts/Roboto-Medium.ttf'), 40)
fontHorizontal = ImageFont.truetype(os.path.join(fontdir,'googlefonts/Roboto-Medium.ttf'), 50)
font_date = ImageFont.truetype(os.path.join(fontdir,'PixelSplitter-Bold.ttf'),11)

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
        logging.info("No internet")
        return False


def getData(config,whichcoin,fiat):
    """
    The function to update the ePaper display. There are two versions of the layout. One for portrait aspect ratio, one for landscape.
    """
    logging.info("Getting Data")
    days_ago=int(config['ticker']['sparklinedays'])   
    endtime = int(round(time.time()))
    starttime = endtime - 60*60*24*days_ago
    starttimeseconds = round(starttime)  
    endtimeseconds = round(endtime)      
    # Get the price 

    if config['ticker']['exchange']=='default' or fiat!='usd':
        geckourl = "https://api.coingecko.com/api/v3/coins/markets?vs_currency="+fiat+"&ids="+whichcoin
        logging.info(geckourl)
        rawlivecoin = requests.get(geckourl).json()
        liveprice= rawlivecoin[0]   
        pricenow= float(liveprice['current_price'])
    else:
        geckourl= "https://api.coingecko.com/api/v3/exchanges/"+config['ticker']['exchange']+"/tickers?coin_ids="+whichcoin+"&include_exchange_logo=false"
        logging.info(geckourl)
        rawlivecoin = requests.get(geckourl).json()
        liveprice= rawlivecoin['tickers'][0]
        if  liveprice['target']!='USD':
            logging.info("The exhange is not listing in USD, misconfigured - shutting down script")
            beanaproblem()
            sys.exit()
        pricenow= float(liveprice['last'])
    logging.info("Got Live Data From CoinGecko")
    geckourlhistorical = "https://api.coingecko.com/api/v3/coins/"+whichcoin+"/market_chart/range?vs_currency="+fiat+"&from="+str(starttimeseconds)+"&to="+str(endtimeseconds)
    logging.info(geckourlhistorical)
    rawtimeseries = requests.get(geckourlhistorical).json()
    logging.info("Got price for the last "+str(days_ago)+" days from CoinGecko")
    timeseriesarray = rawtimeseries['prices']
    timeseriesstack = []
    length=len (timeseriesarray)
    i=0
    while i < length:
        timeseriesstack.append(float (timeseriesarray[i][1]))
        i+=1

    timeseriesstack.append(pricenow)
    return timeseriesstack

def beanaproblem():
#   A visual cue that the wheels have fallen off
    thebean = Image.open(os.path.join(picdir,'thebean.bmp'))
    epd = epd2in7.EPD()
    epd.Init_4Gray()
    image = Image.new('L', (epd.height, epd.width), 255)    # 255: clear the image with white
    draw = ImageDraw.Draw(image)
    image.paste(thebean, (60,15))
    image = ImageOps.mirror(image)
    epd.display_4Gray(epd.getbuffer_4Gray(image))
    epd.sleep()
    epd2in7.epdconfig.module_exit()

def makeSpark(pricestack):
    # Draw and save the sparkline that represents historical data

    # Subtract the mean from the sparkline to make the mean appear on the plot (it's really the x axis)    
    x = pricestack-np.mean(pricestack)

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
    plt.savefig(os.path.join(picdir,'spark.png'), dpi=17)
    imgspk = Image.open(os.path.join(picdir,'spark.png'))
    file_out = os.path.join(picdir,'spark.bmp')
    imgspk.save(file_out) 
    plt.clf() # Close plot to prevent memory error


def updateDisplay(config,pricestack,whichcoin,fiat):
    """   
    Takes the price data, the desired coin/fiat combo along with the config info for formatting
    if config is re-written following adustment we could avoid passing the last two arguments as
    they will just be the first two items of their string in config 
    """
    days_ago=int(config['ticker']['sparklinedays'])   
    symbolstring=currency.symbol(fiat.upper())
    if fiat=="jpy":
        symbolstring="¥"

    pricenow = pricestack[-1]
    currencythumbnail= 'currency/'+whichcoin+'.bmp'
    tokenimage = Image.open(os.path.join(picdir,currencythumbnail))
    sparkbitmap = Image.open(os.path.join(picdir,'spark.bmp'))


    pricechange = str("%+d" % round((pricestack[-1]-pricestack[0])/pricestack[-1]*100,2))+"%"
    if pricenow > 1000:
        pricenowstring =format(int(pricenow),",")
    else:
        pricenowstring =str(float('%.5g' % pricenow))

    if config['display']['orientation'] == 0 or config['display']['orientation'] == 180 :
        epd = epd2in7.EPD()
        epd.Init_4Gray()
        image = Image.new('L', (epd.width, epd.height), 255)    # 255: clear the image with white
        draw = ImageDraw.Draw(image)              
        draw.text((110,80),str(days_ago)+"day :",font =font_date,fill = 0)
        draw.text((110,95),pricechange,font =font_date,fill = 0)
        # Print price to 5 significant figures
        draw.text((15,200),symbolstring+pricenowstring,font =font,fill = 0)
        draw.text((10,10),str(time.strftime("%H:%M %a %d %b %Y")),font =font_date,fill = 0)
        image.paste(tokenimage, (10,25))
        image.paste(sparkbitmap,(10,125))
        if config['display']['orientation'] == 180 :
            image=image.rotate(180, expand=True)


    if config['display']['orientation'] == 90 or config['display']['orientation'] == 270 :
        epd = epd2in7.EPD()
        epd.Init_4Gray()
        image = Image.new('L', (epd.height, epd.width), 255)    # 255: clear the image with white
        draw = ImageDraw.Draw(image)   
        draw.text((110,90),str(days_ago)+"day : "+pricechange,font =font_date,fill = 0)
        # Print price to 5 significant figures
 #       draw.text((20,120),symbolstring,font =fonthiddenprice,fill = 0)
        draw.text((10,120),symbolstring+pricenowstring,font =fontHorizontal,fill = 0)
        image.paste(sparkbitmap,(80,40))
        image.paste(tokenimage, (0,0))
        draw.text((95,15),str(time.strftime("%H:%M %a %d %b %Y")),font =font_date,fill = 0)
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

def currencystringtolist(currstring):
    # Takes the string for currencies in the config.yaml file and turns it into a list
    curr_list = currstring.split(",")
    curr_list = [x.strip(' ') for x in curr_list]
    return curr_list

def currencycycle(curr_list):
    # Rotate the array of currencies from config.... [a b c] becomes [b c a]
    curr_list = curr_list[1:]+curr_list[:1]
    return curr_list    

def main():
    
    def fullupdate():
        """  
        The steps required for a full update of the display
        Earlier versions of the code didn't grab new data for some operations
        but the e-Paper is too slow to bother the coingecko API 
        """
        try:
            pricestack=getData(config,CURRENCY,FIAT)
            # generate sparkline
            makeSpark(pricestack)
            # update display
            updateDisplay(config, pricestack, CURRENCY,FIAT)
            lastgrab=time.time()
        except:
            beanaproblem()
            time.sleep(10)
            lastgrab=lastcoinfetch
        return lastgrab

    def configwrite():
        """  
        Write the config file following an adjustment made using the buttons
        This is so that the unit returns to its last state after it has been 
        powered off 
        """ 
        config['ticker']['currency']=",".join(crypto_list)
        config['ticker']['fiatcurrency']=",".join(fiat_list)
        with open(configfile, 'w') as f:
            data = yaml.dump(config, f)    

    logging.basicConfig(level=logging.DEBUG)

    try:
        logging.info("epd2in7 BTC Frame")
#       Get the configuration from config.yaml
        with open(configfile) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        logging.info(config)
        config['display']['orientation']=int(config['display']['orientation'])

        crypto_list = currencystringtolist(config['ticker']['currency'])
        logging.info(crypto_list) 

        fiat_list=currencystringtolist(config['ticker']['fiatcurrency'])
        logging.info(fiat_list) 

        CURRENCY=crypto_list[0]
        FIAT=fiat_list[0]

        logging.info(CURRENCY)
        logging.info(FIAT)

        GPIO.setmode(GPIO.BCM)
        key1 = 5
        key2 = 6
        key3 = 13
        key4 = 19

        GPIO.setup(key1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(key2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(key3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(key4, GPIO.IN, pull_up_down=GPIO.PUD_UP)


#       Note that there has been no data pull yet
        datapulled=False 
#       Time of start
        lastcoinfetch = time.time()
     
        while True:
            key1state = GPIO.input(key1)
            key2state = GPIO.input(key2)
            key3state = GPIO.input(key3)
            key4state = GPIO.input(key4)

            if internet():
                if key1state == False:
                    logging.info('Cycle currencies')
                    crypto_list = currencycycle(crypto_list)
                    CURRENCY=crypto_list[0]
                    logging.info(CURRENCY)
                    lastcoinfetch=fullupdate()
                    configwrite()
                if key2state == False:
                    logging.info('Rotate - 90')
                    config['display']['orientation'] = (config['display']['orientation']+90) % 360
                    lastcoinfetch=fullupdate()
                    configwrite()
                if key3state == False:
                    logging.info('Invert Display')
                    config['display']['inverted']= not config['display']['inverted']
                    lastcoinfetch=fullupdate()
                    configwrite()
                if key4state == False:
                    logging.info('Cycle fiat')
                    fiat_list = currencycycle(fiat_list)
                    FIAT=fiat_list[0]
                    logging.info(FIAT)
                    lastcoinfetch=fullupdate()
                    configwrite()
                if (time.time() - lastcoinfetch > float(config['ticker']['updatefrequency'])) or (datapulled==False):
                    lastcoinfetch=fullupdate()
                    datapulled = True



    except IOError as e:
        logging.info(e)
    
    except KeyboardInterrupt:    
        logging.info("ctrl + c:")
        epd2in7.epdconfig.module_exit()
        exit()

if __name__ == '__main__':
    main()
