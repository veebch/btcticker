#!/usr/bin/python3

"""
  main.py - a script for a cryptocurrency ticker.
    
     Copyright (C) 2023 Veeb Projects https://veeb.ch

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>

"""


from babel.numbers import decimal, format_currency, format_scientific
from babel import Locale
import argparse
import textwrap
import socket
import yaml
import matplotlib.pyplot as plt
from PIL import Image, ImageOps
from PIL import ImageFont
from PIL import ImageDraw
import currency
import os
import sys
import logging
import RPi.GPIO as GPIO

from waveshare_epd import epd4in0e 
import time
import requests
import urllib
import json
import matplotlib as mpl

mpl.use("Agg")

dirname = os.path.dirname(__file__)
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "images")
fontdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fonts/googlefonts")
configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.yaml")
font_date = ImageFont.truetype(os.path.join(fontdir, "PixelSplitter-Bold.ttf"), 14)
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36",
    # "x-cg-demo-api-key": "$COINGECKO_API_KEY"
}
button_pressed = 0


def internet(hostname="google.com"):
    """
    Host: google.com
    """
    try:
        # see if we can resolve the host name -- tells us if there is
        # a DNS listening
        host = socket.gethostbyname(hostname)
        # connect to the host -- tells us if the host is actually
        # reachable
        s = socket.create_connection((host, 80), 2)
        s.close()
        return True
    except:
        logging.info("Google says No")
        time.sleep(1)
    return False


def human_format(num):
    num = float("{:.3g}".format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return "{}{}".format(
        "{:f}".format(num).rstrip("0").rstrip("."), ["", "K", "M", "B", "T"][magnitude]
    )


def _place_text(
    img, text, x_offset=0, y_offset=0, fontsize=40, fontstring="Forum-Regular", fill=0
):
    """
    Put some centered text at a location on the image.
    """
    draw = ImageDraw.Draw(img)
    try:
        filename = os.path.join(dirname, "./fonts/googlefonts/" + fontstring + ".ttf")
        font = ImageFont.truetype(filename, fontsize)
    except OSError:
        font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", fontsize)
    img_width, img_height = img.size
    try:
      text_width = font.getbbox(text)[2]
      text_height = font.getbbox(text)[3]
    except:
      text_width = font.getsize(text)[0]
      text_height = font.getsize(text)[1]
    draw_x = (img_width - text_width) // 2 + x_offset
    draw_y = (img_height - text_height) // 2 + y_offset
    draw.text((draw_x, draw_y), text, font=font, fill=fill)


def writewrappedlines(
    img, text, fontsize=16, y_text=20, height=15, width=25, fontstring="Roboto-Light"
):
    lines = textwrap.wrap(text, width)
    numoflines = 0
    for line in lines:
        _place_text(img, line, 0, y_text, fontsize, fontstring)
        y_text += height
        numoflines += 1
    return img


def getgecko(url):
    try:
        geckojson = requests.get(url, headers=headers).json()
        connectfail = False
    except requests.exceptions.RequestException as e:
        logging.error("Issue with CoinGecko")
        connectfail = True
        geckojson = {}
    return geckojson, connectfail


def getData(config, other):
    """
    Modified to handle multiple coins and fetch images
    """
    sleep_time = 10
    num_retries = 5
    coins_list = currencystringtolist(config["ticker"]["currency"])
    whichcoin, fiat = configtocoinandfiat(config)
    logging.info("Getting Data")
    days_ago = int(config["ticker"]["sparklinedays"])
    endtime = int(time.time())
    starttime = endtime - 60 * 60 * 24 * days_ago
    
    all_price_data = []
    
    for coin in coins_list:
        # Fetch coin image
        get_coin_image(coin)
        
        timeseriesstack = []
        geckourlhistorical = (
            "https://api.coingecko.com/api/v3/coins/"
            + coin
            + "/market_chart/range?vs_currency="
            + fiat
            + "&from="
            + str(starttime)
            + "&to="
            + str(endtime)
        )
        
        for x in range(0, num_retries):
            rawtimeseries, connectfail = getgecko(geckourlhistorical)
            if not connectfail:
                timeseriesarray = rawtimeseries["prices"]
                timeseriesstack = [float(price[1]) for price in timeseriesarray]
                
                # Get current price
                geckourl = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={fiat}&ids={coin}"
                rawlivecoin, connectfail = getgecko(geckourl)
                
                if not connectfail:
                    liveprice = rawlivecoin[0]
                    timeseriesstack.append(float(liveprice["current_price"]))
                    break
                
            time.sleep(sleep_time)
            sleep_time *= 2
            
        all_price_data.append(timeseriesstack)
        
        # Create separate spark image for each coin
        makeSpark(timeseriesstack, coin)
        
    return all_price_data, other


def beanaproblem(message):
    #   A visual cue that the wheels have fallen off
    thebean = Image.open(os.path.join(picdir, "thebean.bmp"))
    # 255: clear the image with white
    image = Image.new("L", (400, 600), 255)
    draw = ImageDraw.Draw(image)
    image.paste(thebean, (60, 45))
    draw.text(
        (95, 15), str(time.strftime("%-H:%M %p, %-d %b %Y")), font=font_date, fill=0
    )
    writewrappedlines(image, "Issue: " + message)
    return image


def makeSpark(pricestack, coin_id):
    # Draw and save the sparkline that represents historical data
    # Subtract the mean from the sparkline to make the mean appear on the plot (it's really the x axis)
    themean = sum(pricestack) / float(len(pricestack))
    x = [xx - themean for xx in pricestack]
    
    # Calculate price change to determine color
    price_change = (pricestack[-1] - pricestack[0]) / pricestack[0]
    line_color = '#00ff00' if price_change >= 0 else '#ff0000'  # Pure green if positive, pure red if negative
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 3))
    plt.plot(x, color=line_color, linewidth=6)
    plt.plot(len(x) - 1, x[-1], color=line_color, marker='o')
    
    # Remove the Y axis
    for k, v in ax.spines.items():
        v.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Make the horizontal line match the chart color
    ax.axhline(c=line_color, linewidth=4, linestyle=(0, (5, 2, 1, 2)))
    
    # Save the resulting png file to the images directory
    plt.savefig(os.path.join(picdir, f"spark_{coin_id}.png"), dpi=17)
    
    # Convert to BMP with color
    imgspk = Image.open(os.path.join(picdir, f"spark_{coin_id}.png"))
    imgspk = imgspk.convert('RGB')  # Convert to RGB instead of L (grayscale)
    file_out = os.path.join(picdir, f"spark_{coin_id}.bmp")
    imgspk.save(file_out)
    
    plt.close(fig)
    plt.cla()  # Close plot to prevent memory error
    ax.cla()  # Close axis to prevent memory error
    imgspk.close()
    return


def custom_format_currency(value, currency, locale):
    value = decimal.Decimal(value)
    locale = Locale.parse(locale)
    pattern = locale.currency_formats["standard"]
    force_frac = (0, 0) if value == int(value) else None
    return pattern.apply(value, locale, currency=currency, force_frac=force_frac)


def updateDisplay(config, price_data, other):
    """
    Takes the price data and displays multiple coins simultaneously on the screen
    """
    whichcoin, fiat = configtocoinandfiat(config)
    coins_list = currencystringtolist(config["ticker"]["currency"])
    days_ago = int(config["ticker"]["sparklinedays"])

    # Create new white image
    image = Image.new("L", (400, 600), 255)
    draw = ImageDraw.Draw(image)

    # Calculate height for each coin section based on number of coins
    num_coins = len(coins_list)
    section_height = 600 // num_coins

    # Draw timestamp at the top
    if "24h" in config["display"] and config["display"]["24h"]:
        timestamp = str(time.strftime("%-H:%M, %d %b %Y"))
    else:
        timestamp = str(time.strftime("%-I:%M %p, %d %b %Y"))
    draw.text((10, 10), timestamp, font=font_date, fill=0)

    # Set locale
    if "locale" in config["display"]:
        localetag = config["display"]["locale"]
    else:
        localetag = "en_US"

    # Draw each coin's information
    for i, (coin, pricestack) in enumerate(zip(coins_list, price_data)):
        y_offset = i * section_height + 40  # Start below timestamp
        
        # Get price and price change
        coin_price = pricestack[-1]
        pricechangeraw = round((pricestack[-1] - pricestack[0]) / pricestack[0] * 100, 2)
        pricechange = str("%+.2f" % pricechangeraw) + "%"

        # Format price string
        fiatupper = fiat.upper()
        if fiat.upper() == "USDT":
            fiatupper = "USD"
        if fiat.upper() == "BTC":
            fiatupper = "₿"

        if coin_price > 10000:
            pricestring = custom_format_currency(int(coin_price), fiatupper, localetag)
        elif coin_price > 0.01:
            pricestring = format_currency(coin_price, fiatupper, locale=localetag, decimal_quantization=False)
        else:
            pricestring = format_currency(coin_price, fiatupper, locale=localetag, decimal_quantization=False)

        try:
            # Load and resize coin image to 16x16
            coin_image = Image.open(os.path.join(picdir, f"coin_{coin}.bmp"))
            coin_image = coin_image.resize((16, 16))
            image.paste(coin_image, (10, y_offset + 2))  # +2 for vertical alignment with text
            name_x = 32  # Space for 16px image + 6px padding
        except:
            name_x = 10
            
        # Draw coin information
        draw.text((name_x, y_offset), coin.upper(), font=font_date, fill=0)
        draw.text((name_x, y_offset + 20), pricestring, font=font_date, fill=0)
        draw.text((name_x, y_offset + 40), f"{days_ago}d: {pricechange}", font=font_date, fill=0)

        # Draw sparkline
        sparkbitmap = Image.open(os.path.join(picdir, f"spark_{coin}.bmp"))
        sparkbitmap = sparkbitmap.resize((200, 50))  # Resize sparkline to fit
        image.paste(sparkbitmap, (180, y_offset))

    # Invert if needed
    if config["display"]["inverted"] == True:
        image = ImageOps.invert(image)

    return image


def currencystringtolist(currstring):
    # Takes the string for currencies in the config.yaml file and turns it into a list
    curr_list = currstring.split(",")
    curr_list = [x.strip(" ") for x in curr_list]
    return curr_list


def currencycycle(curr_string):
    curr_list = currencystringtolist(curr_string)
    # Rotate the array of currencies from config.... [a b c] becomes [b c a]
    curr_list = curr_list[1:] + curr_list[:1]
    return curr_list


def display_image(img):
    epd = epd4in0e.EPD()
    epd.init()
    # Convert the image to the display's color mode
    if img.mode != "RGB":
        img = img.convert("RGB")
    
    # Get the color buffer instead of black and white
    epd.display(epd.getbuffer(img))
    epd.sleep()
    thekeys = initkeys()
    #   Have to remove and add key events to make them work again
    removekeyevent(thekeys)
    addkeyevent(thekeys)
    logging.info("Sent image to screen")
    return


def initkeys():
    key1 = 5
    key2 = 6
    key3 = 13
    key4 = 19
    logging.debug("Setup GPIO keys")
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(key1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(key2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(key3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(key4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    thekeys = [key1, key2, key3, key4]
    return thekeys


def addkeyevent(thekeys):
    #   Add keypress events
    logging.debug("Add key events")
    btime = 500
    GPIO.add_event_detect(thekeys[0], GPIO.FALLING, callback=keypress, bouncetime=btime)
    GPIO.add_event_detect(thekeys[1], GPIO.FALLING, callback=keypress, bouncetime=btime)
    GPIO.add_event_detect(thekeys[2], GPIO.FALLING, callback=keypress, bouncetime=btime)
    GPIO.add_event_detect(thekeys[3], GPIO.FALLING, callback=keypress, bouncetime=btime)
    return


def removekeyevent(thekeys):
    #   Remove keypress events
    logging.debug("Remove key events")
    GPIO.remove_event_detect(thekeys[0])
    GPIO.remove_event_detect(thekeys[1])
    GPIO.remove_event_detect(thekeys[2])
    GPIO.remove_event_detect(thekeys[3])
    return


def keypress(channel):
    global button_pressed
    with open(configfile) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    lastcoinfetch = time.time()
    if channel == 5 and button_pressed == 0:
        logging.info("Cycle currencies")
        button_pressed = 1
        crypto_list = currencycycle(config["ticker"]["currency"])
        config["ticker"]["currency"] = ",".join(crypto_list)
        lastcoinfetch = fullupdate(config, lastcoinfetch)
        configwrite(config)
        return
    elif channel == 6 and button_pressed == 0:
        logging.info("Rotate - 90")
        button_pressed = 1
        config["display"]["orientation"] = (config["display"]["orientation"] + 90) % 360
        lastcoinfetch = fullupdate(config, lastcoinfetch)
        configwrite(config)
        return
    elif channel == 13 and button_pressed == 0:
        logging.info("Invert Display")
        button_pressed = 1
        config["display"]["inverted"] = not config["display"]["inverted"]
        lastcoinfetch = fullupdate(config, lastcoinfetch)
        configwrite(config)
        return
    elif channel == 19 and button_pressed == 0:
        logging.info("Cycle fiat")
        button_pressed = 1
        fiat_list = currencycycle(config["ticker"]["fiatcurrency"])
        config["ticker"]["fiatcurrency"] = ",".join(fiat_list)
        lastcoinfetch = fullupdate(config, lastcoinfetch)
        configwrite(config)
        return
    return


def configwrite(config):
    """
    Write the config file following an adjustment made using the buttons
    This is so that the unit returns to its last state after it has been
    powered off
    """
    with open(configfile, "w") as f:
        data = yaml.dump(config, f)
    #   Reset button pressed state after config is written
    global button_pressed
    button_pressed = 0


def fullupdate(config, lastcoinfetch):
    """
    The steps required for a full update of the display
    Earlier versions of the code didn't grab new data for some operations
    but the e-Paper is too slow to bother the coingecko API
    """
    other = {}
    try:
        price_data, ATH = getData(config, other)
        # update display
        image = updateDisplay(config, price_data, other)
        display_image(image)
        lastgrab = time.time()
        time.sleep(0.2)
    except Exception as e:
        message = "Data pull/print problem"
        image = beanaproblem(
            str(e)
            + " Check your connection. Error at Line: "
            + str(e.__traceback__.tb_lineno)
        )
        display_image(image)
        time.sleep(20)
        lastgrab = lastcoinfetch
    return lastgrab


def configtocoinandfiat(config):
    crypto_list = currencystringtolist(config["ticker"]["currency"])
    fiat_list = currencystringtolist(config["ticker"]["fiatcurrency"])
    currency = crypto_list[0]
    fiat = fiat_list[0]
    return currency, fiat


def gettrending(config):
    print("ADD TRENDING")
    coinlist = config["ticker"]["currency"]
    url = "https://api.coingecko.com/api/v3/search/trending"
    #   Cycle must be true if trending mode is on
    config["display"]["cycle"] = True
    trendingcoins = requests.get(url, headers=headers).json()
    for i in range(0, (len(trendingcoins["coins"]))):
        print(trendingcoins["coins"][i]["item"]["id"])
        coinlist += "," + str(trendingcoins["coins"][i]["item"]["id"])
    config["ticker"]["currency"] = coinlist
    return config


def get_coin_image(coin_id):
    """
    Fetches and saves the coin image from CoinGecko
    """
    try:
        # Get coin data including image URL
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=false&community_data=false&developer_data=false&sparkline=false"
        response = requests.get(url, headers=headers)
        data = response.json()
        image_url = data['image']['small']  # Using small image size (24x24)
        
        # Download and save the image
        image_response = requests.get(image_url)
        if image_response.status_code == 200:
            image_path = os.path.join(picdir, f"coin_{coin_id}.png")
            with open(image_path, 'wb') as f:
                f.write(image_response.content)
            
            # Convert to BMP
            img = Image.open(image_path)
            img = img.convert('L')  # Convert to grayscale
            bmp_path = os.path.join(picdir, f"coin_{coin_id}.bmp")
            img.save(bmp_path)
            return True
    except Exception as e:
        logging.error(f"Error fetching image for {coin_id}: {str(e)}")
        return False


def main():
    GPIO.setmode(GPIO.BCM)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log", default="info", help="Set the log level (default: info)"
    )
    args = parser.parse_args()

    loglevel = getattr(logging, args.log.upper(), logging.WARN)
    logging.basicConfig(level=loglevel)
    # Set timezone based on ip address
    try:
        os.system("sudo /home/pi/.local/bin/tzupdate")
    except:
        logging.info("Timezone Not Set")
    try:
        logging.info("epd2in7 BTC Frame")
        #       Get the configuration from config.yaml
        with open(configfile) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        logging.info(config)
        config["display"]["orientation"] = int(config["display"]["orientation"])
        staticcoins = config["ticker"]["currency"]
        #       Get the buttons for 2.7in EPD set up
        thekeys = initkeys()
        #       Add key events
        addkeyevent(thekeys)
        #       Note how many coins in original config file
        howmanycoins = len(config["ticker"]["currency"].split(","))
        #       Note that there has been no data pull yet
        datapulled = False
        #       Time of start
        lastcoinfetch = time.time()
        #       Quick Sanity check on update frequency, waveshare says no faster than 180 seconds, but we'll make 60 the lower limit
        if float(config["ticker"]["updatefrequency"]) < 60:
            logging.info("Throttling update frequency to 60 seconds")
            updatefrequency = 60.0
        else:
            updatefrequency = float(config["ticker"]["updatefrequency"])
        while internet() == False:
            logging.info("Waiting for internet")
        while True:
            if config["display"]["trendingmode"] == True:
                # The hard-coded 7 is for the number of trending coins to show. Consider revising
                if (
                    time.time() - lastcoinfetch > (7 + howmanycoins) * updatefrequency
                ) or (datapulled == False):
                    # Reset coin list to static (non trending coins from config file)
                    config["ticker"]["currency"] = staticcoins
                    config = gettrending(config)
            if (time.time() - lastcoinfetch > updatefrequency) or (datapulled == False):
                if config["display"]["cycle"] == True and (datapulled == True):
                    crypto_list = currencycycle(config["ticker"]["currency"])
                    fiat_list = currencycycle(config["ticker"]["fiatcurrency"])
                    config["ticker"]["currency"] = ",".join(crypto_list)
                    if "cyclefiat" in config["display"] and (
                        config["display"]["cyclefiat"] is True
                    ):
                        config["ticker"]["fiatcurrency"] = ",".join(fiat_list)
                    # configwrite(config)
                lastcoinfetch = fullupdate(config, lastcoinfetch)
                datapulled = True
            #           Reduces CPU load during that while loop
            time.sleep(0.01)
    except IOError as e:
        logging.error(e)
        image = beanaproblem(str(e) + " Line: " + str(e.__traceback__.tb_lineno))
        display_image(image)
    except Exception as e:
        logging.error(e)
        image = beanaproblem(str(e) + " Line: " + str(e.__traceback__.tb_lineno))
        display_image(image)
    except KeyboardInterrupt:
        logging.info("ctrl + c:")
        image = beanaproblem("Keyboard Interrupt")
        display_image(image)
        epd4in0e.epdconfig.module_exit()
        GPIO.cleanup()
        exit()


if __name__ == "__main__":
    main()
