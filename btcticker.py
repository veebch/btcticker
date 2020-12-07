#!/usr/bin/python3
from PIL import Image, ImageOps
from PIL import ImageFont
from PIL import ImageDraw
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
		print(ex)
		return False


def getData(whichcoin):
	"""
	The function to update the ePaper display. There are two versions of the layout. One for portrait aspect ratio, one for landscape.
	"""
    # Get the week window in msec from epoch. This is used in the api calls
	logging.info("Getting Data")   
	now_msec_from_epoch = int(round(time.time() * 1000))
	days_ago = 7
	endtime = now_msec_from_epoch
	starttime = endtime - 1000*60*60*24*days_ago
	starttimeseconds = round(starttime/1000)  #CoinGecko Uses seconds
	endtimeseconds = round(endtime/1000)      #CoinGecko Uses seconds

    # Get the live price 
	try:
		geckourl = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids="+whichcoin
		logging.info(geckourl)
		rawlivecoin = requests.get(geckourl).json()
		liveprice= rawlivecoin[0]   
		pricenow= float(liveprice['current_price'])
		logging.info("Got Live Data From CoinGecko")
	except urllib.error.URLError:
		coinapiurl= "https://api.coincap.io/v2/assets/"+whichcoin+"/"
		rawlivecoin = requests.get(coinapiurl).json()
		liveprice= rawlivecoin['data']   
		pricenow = float(liveprice['priceUsd'])
		logging.info("Got Live Data From CoinApi")
    
    # Get the time series
	try:
		#Coingecko as first choice 
		#example call https://api.coingecko.com/api/v3/coins/ethereum/market_chart/range?vs_currency=usd&from=1592577232&to=1622577232

		geckourlhistorical = "https://api.coingecko.com/api/v3/coins/"+whichcoin+"/market_chart/range?vs_currency=usd&from="+str(starttimeseconds)+"&to="+str(endtimeseconds)
		logging.info(geckourlhistorical)
		rawtimeseries = requests.get(geckourlhistorical).json()
		logging.info("Got Historical Data For Last Week from CoinGecko")
		timeseriesarray = rawtimeseries['prices']
		timeseriesstack = []
		length=len (timeseriesarray)
		i=0
		while i < length:
			timeseriesstack.append(float (timeseriesarray[i][1]))
			i+=1

	except urllib.error.URLError:
		# Form the Coinapi call
		coinapi = "https://api.coincap.io/v2/assets/"+whichcoin+"/history?interval=h1&start="+str(starttime)+"&end="+str(endtime)
		rawtimeseries = requests.get(coinapi).json()
		logging.info("Got Historic Data For Last Week from CoinApi")
		timeseriesarray = rawtimeseries['data']
		timeseriesstack = []
		length=len (timeseriesarray)
		i=0
		while i < length:
			timeseriesstack.append(float (timeseriesarray[i]['priceUsd']))
			i+=1

	

	# Add live price to timeseriesstack
	timeseriesstack.append(pricenow)
	return timeseriesstack

def makeSpark(pricestack):

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


def updateDisplay(config,pricestack,whichcoin):

  

	pricenow = pricestack[-1]
	currencythumbnail= 'currency/'+whichcoin+'.bmp'
	tokenimage = Image.open(os.path.join(picdir,currencythumbnail))
	sparkbitmap = Image.open(os.path.join(picdir,'spark.bmp'))
	if config['ticker']['hidden'] == True:
		if config['display']['orientation'] == 0 or config['display']['orientation'] == 180 :
			epd = epd2in7.EPD()
			epd.Init_4Gray()
			image = Image.new('L', (epd.width, epd.height), 255)    # 255: clear the image with white
			image.paste(tokenimage, (10,20)) 
			draw = ImageDraw.Draw(image)
			draw.text((5,200),"1 "+ whichcoin,font =font,fill = 0)             
			draw.text((0,10),str(time.strftime("%c")),font =font_date,fill = 0)
			if config['display']['orientation'] == 180 :
				image=image.rotate(180, expand=True)


		if config['display']['orientation'] == 90 or config['display']['orientation'] == 270 :
			epd = epd2in7.EPD()
			epd.Init_4Gray()
			image = Image.new('L', (epd.height, epd.width), 255)    # 255: clear the image with white
			image.paste(tokenimage, (0,0))
			draw = ImageDraw.Draw(image)
			draw.text((20,120),"1 "+ whichcoin,font =fontHorizontal,fill = 0)
			draw.text((85,5),str(time.strftime("%c")),font =font_date,fill = 0)
			if config['display']['orientation'] == 270 :
				image=image.rotate(180, expand=True)
	#       This is a hack to deal with the mirroring that goes on in 4Gray Horizontal
			image = ImageOps.mirror(image)
	else:
		if config['display']['orientation'] == 0 or config['display']['orientation'] == 180 :
			epd = epd2in7.EPD()
			epd.Init_4Gray()
			image = Image.new('L', (epd.width, epd.height), 255)    # 255: clear the image with white
			draw = ImageDraw.Draw(image)              
			draw.text((110,80),"7day :",font =font_date,fill = 0)
			draw.text((110,95),str("%+d" % round((pricestack[-1]-pricestack[0])/pricestack[-1]*100,2))+"%",font =font_date,fill = 0)
			# Print price to 5 significant figures
			draw.text((5,200),"$"+format(float('%.5g' % pricenow),","),font =font,fill = 0)
			draw.text((0,10),str(time.strftime("%c")),font =font_date,fill = 0)
			image.paste(tokenimage, (10,25))
			image.paste(sparkbitmap,(10,125))
			if config['display']['orientation'] == 180 :
				image=image.rotate(180, expand=True)


		if config['display']['orientation'] == 90 or config['display']['orientation'] == 270 :
			epd = epd2in7.EPD()
			epd.Init_4Gray()
			image = Image.new('L', (epd.height, epd.width), 255)    # 255: clear the image with white
			draw = ImageDraw.Draw(image)   
			draw.text((100,100),"7day : "+str("%+d" % round((pricestack[-1]-pricestack[0])/pricestack[-1]*100,2))+"%",font =font_date,fill = 0)
			# Print price to 5 significant figures
			draw.text((20,120),"$"+format(float('%.5g' % pricenow),","),font =fontHorizontal,fill = 0)
			image.paste(sparkbitmap,(80,50))
			image.paste(tokenimage, (0,0))
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

		with open(configfile) as f:
			config = yaml.load(f, Loader=yaml.FullLoader)
		logging.info(config)
		GPIO.setmode(GPIO.BCM)
		config['display']['orientation']=int(config['display']['orientation'])

		currencystring = config['ticker']['currency']
		crypto_list = currencystring.split(",")
		crypto_list = [x.strip(' ') for x in crypto_list]
		logging.info(crypto_list) 

		coinnumber = 0
		CURRENCY=crypto_list[coinnumber]
		logging.info(CURRENCY)
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
					# Rotate the array of currencies from config.... [a b c] becomes [b c a]
					crypto_list = crypto_list[1:]+crypto_list[:1]
					CURRENCY=crypto_list[0]
					# Write back to config file
					config['ticker']['currency']=",".join(crypto_list)
					with open(configfile, 'w') as f:
					   data = yaml.dump(config, f)
					logging.info(CURRENCY)
					# get data
					pricestack=getData(CURRENCY)
					# save time of last data update 
					lastcoinfetch = time.time()
					# generate sparkline
					makeSpark(pricestack)
					# update display
					updateDisplay(config, pricestack, CURRENCY)
				if key2state == False:
					logging.info('Rotate - 90')
					config['display']['orientation'] = (config['display']['orientation']+90) % 360
					time.sleep(0.2)
					# updatedisplay
					pricestack=getData(CURRENCY)
					lastcoinfetch = time.time()
					updateDisplay(config, pricestack, CURRENCY)
					with open(configfile, 'w') as f:
					   data = yaml.dump(config, f)
				if key3state == False:
					logging.info('Invert Display')
					if config['display']['inverted'] == True:
					   config['display']['inverted'] = False
					else:
					   config['display']['inverted'] = True 
					#update display
					pricestack=getData(CURRENCY)
					lastcoinfetch = time.time()
					updateDisplay(config, pricestack, CURRENCY)
					with open(configfile, 'w') as f:
					   data = yaml.dump(config, f)
					lastcoinfetch=time.time() 
					time.sleep(0.2)
				if key4state == False:
					logging.info('Hide')
					if config['ticker']['hidden'] == True:
						config['ticker']['hidden'] = False
					else:
						config['ticker']['hidden'] = True
					pricestack=getData(CURRENCY)
					lastcoinfetch = time.time()
					updateDisplay(config, pricestack, CURRENCY)
					time.sleep(0.2)
				if (time.time() - lastcoinfetch > float(config['ticker']['updatefrequency'])) or (datapulled==False):
					# get data
					pricestack=getData(CURRENCY)
					# save time of last data update 
					lastcoinfetch = time.time()
					# generate sparkline
					makeSpark(pricestack)
					# update display
					updateDisplay(config, pricestack,CURRENCY)
					# Note that we've visited the internet
					datapulled = True
					lastcoinfetch=time.time()
					time.sleep(0.2)

	except IOError as e:
		logging.info(e)
	
	except KeyboardInterrupt:    
		logging.info("ctrl + c:")
		epd2in7.epdconfig.module_exit()
		exit()

if __name__ == '__main__':
	main()
