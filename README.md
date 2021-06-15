# Cryptocurrency ePaper Ticker 
(supports all 7000+ coins/currencies listed on [CoinGecko](https://api.coingecko.com/api/v3/coins/list))

An ePaper Cryptocurrency price ticker that runs as a Python script on a Raspberry Pi connected to a [Waveshare 2.7 inch monochrome ePaper display](https://www.waveshare.com/wiki/2.7inch_e-Paper_HAT). The script periodically (every 5 mins by default) takes data from CoinGecko and prints a summary to the ePaper.

A few minutes work gives you a desk ornament that will tastefully and unobtrusively monitor a coin's journey moonward.

![Action Shot](/images/actionshot/BasicLunar.jpg)


# Getting started

## Prerequisites

(These instructions assume that your Raspberry Pi is already connected to the Internet, happily running pip and has Python3 installed)

If you are running the Pi headless, connect to your Raspberry Pi using ssh.

Install the Waveshare Python module following the instructions on their [Wiki](https://www.waveshare.com/wiki/2.7inch_e-Paper_HAT) under the tab Hardware/Software setup.

(To install the waveshare_epd python module, you need to run the setup file in their repository - also, be sure not to install Jetson libraries on a Pi)

```
cd e-Paper/RaspberryPi_JetsonNano/python
sudo python3 setup.py install
```
## Install & Run

Copy the files from this repository onto the Pi, or clone using:

```
cd ~
git clone https://github.com/llvllch/btcticker.git
cd btcticker
```


Install the required modules using pip:

```
python3 -m pip install -r requirements.txt
```

If you'd like the script to persist once you close the session, use [screen](https://linuxize.com/post/how-to-use-linux-screen/).

Start a screen session:

```
screen bash
```

Run the script using:

```
python3 btcticker.py
```

Detatch from the screen session using CTRL-A followed by CTRL-D

The ticker will now pull data every 10 minutes and update the display. 

# Interface

The ePaper is slow. There is a lag of a few seconds between button press and a change to the display. 

Here's what the buttons do:
- Button 1: Cycle through the cryptocurrencies listed in config.yaml
- Button 2: Rotate Display -90 degrees
- Button 3: Invert Display
- Button 4: Cycle through the fiat currencies listed in config.yaml

Update frequency can be changed in the config.yaml file (default is 600 seconds).

# Configuration

The file config.yaml contains a number of options that may be tweaked:

```
display:
  cycle: true
  inverted: false
  orientation: 90
  trendingmode: false
  showvolume: false
  showrank: false
ticker:
  currency: bitcoin,ethereum,cardano
  exchange: default
  fiatcurrency: usd,eur,gbp
  sparklinedays: 1 
  updatefrequency: 300
```

- **cycle**: switch the display between the listed currencies if set to **true**, display only the first on the list if set to **false**
- **inverted**: Black text on grey background if **false**. Grey text on black background if **true**
- **orientation**: Screen rotation in degrees , can take values **0,90,180,270**
- **trendingmode**: If **true**, it checks the 7 coins that coingecko lists as trending and also displays them (names are included in display)
- **showvolume, showrank**: **true** to include in display, **false** to omit
- **currency**: the coin(s) you would like to display (must be the coingecko id)
- **exchange**: default means use coingecko price, it can also be set to a specific exchange name such as **gdax** (coinbase), **binance** or **kraken** (full list on coingecko api [page](https://www.coingecko.com/api/documentations/v3)) 
- **fiatcurrency**: currently only uses first one (unless you are cycling with buttons)
- **sparklinedays**: Number of days of historical data appearing on chart
- **updatefrequency**: (in seconds), how often to refresh the display

# Contributing

To contribute, please fork the repository and use a feature branch. Pull requests are welcome.

# Links
[![Watch the video](https://img.youtube.com/vi/DNLUmJb7Mj8/maxresdefault.jpg)](https://youtu.be/DNLUmJb7Mj8) 
- Video of the unit working [here](https://youtu.be/DNLUmJb7Mj8)
- A fully assembled ticker or frames can be obtained at [veeb.ch](http://www.veeb.ch/)

# Troubleshooting

Some people have had errors on a clean install of Rasbian Lite on Pi. If you do, run:

```
sudo apt-get install libopenjp2-7
sudo apt-get install libqt5gui5
sudo apt-get install python-scipy
sudo apt install libatlas-base-dev
```

and re-run the script.

If the unit is freezing, try switching to another power supply. 

# Licencing

GNU GENERAL PUBLIC LICENSE Version 3.0
