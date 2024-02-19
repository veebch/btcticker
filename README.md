[![YouTube Channel Views](https://img.shields.io/youtube/channel/views/UCz5BOU9J9pB_O0B8-rDjCWQ?label=YouTube&style=social)](https://www.youtube.com/channel/UCz5BOU9J9pB_O0B8-rDjCWQ)

[![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white)](https://www.instagram.com/v_e_e_b/)

# Cryptocurrency ePaper Ticker 
(supports all coins/currencies/exchanges listed on [CoinGecko](https://api.coingecko.com/api/v3/coins/list))

An ePaper Cryptocurrency price ticker that runs as a Python script on a Raspberry Pi connected to a [Waveshare 2.7 inch monochrome ePaper display](https://www.waveshare.com/wiki/2.7inch_e-Paper_HAT). The script periodically (every 5 mins by default) takes data from CoinGecko and prints a summary to the ePaper. You can specify the exchange used for price info, as well as the currencies that your chosen coin's prices are in. 

A few minutes work gives you a desk ornament that will tastefully and unobtrusively monitor a coin's journey moonward.

![Action Shot](/images/actionshot/BasicLunar.jpg)


# Getting started

## Prerequisites

(These instructions assume that your Raspberry Pi is already connected to the Internet, happily running `pip` and has `python3` installed)

If you are running the Pi headless, connect to your Raspberry Pi using `ssh`.

Connect to your ticker over ssh and update and install necessary packages 
```
sudo apt-get update
sudo apt-get install -y python3-pip mc git libopenjp2-7
sudo apt-get install -y libatlas-base-dev python3-pil python-numpy python-matplotlib
```

Enable spi (0=on 1=off)

```
sudo raspi-config nonint do_spi 0
```

Now clone the required software (Waveshare libraries and this script)

```
cd ~
git clone https://github.com/waveshare/e-Paper
git clone https://github.com/veebch/btcticker.git
```
Move to the `btcticker` directory, copy the example config to `config.yaml` and move the required part of the waveshare directory to the `btcticker` directory
```
cd btcticker
cp config_example.yaml config.yaml
cp -r ~/e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd .
rm -rf ~/e-Paper
```
Install the required Python3 modules
```
python3 -m pip install -r requirements.txt
```

## Add Autostart

```
cat <<EOF | sudo tee /etc/systemd/system/btcticker.service
[Unit]
Description=btcticker
After=network.target

[Service]
ExecStart=/usr/bin/python3 -u /home/pi/btcticker/btcticker.py
WorkingDirectory=/home/pi/btcticker/
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF
```
Note that this assumes your user is '**pi**'.  If it isn't, change accordingly. Now, simply enable the service you just made and reboot
```  
sudo systemctl enable btcticker.service
sudo systemctl start btcticker.service

sudo reboot
```
# Control via buttons

This only applies if you are going to control configuration via the buttons on the board.

The ePaper is slow. There is a lag of a few seconds between button press and a change to the display. 

Here's what each of the buttons do:
- Button 1: Cycle through the cryptocurrencies listed in config.yaml
- Button 2: Rotate Display -90 degrees
- Button 3: Invert Display
- Button 4: Cycle through the fiat currencies listed in config.yaml

Update frequency can be changed in the configuration file (default is 300 seconds).

# Configuration via config file

The file `config.yaml` (the copy of `config_example.yaml` you made earlier) contains a number of options that can be tweaked:

```
display:
  cycle: true # Setting to true makes the ticker cycle through a list of coins
  cyclefiat: true # Setting to true makes fiat cycle too, so you can do multiple pairs
  inverted: false # true for black text on grey, false for grey text
  orientation: 90 # 90 for horizontal display, buttons on left
  trendingmode: false # Add trending coins to those being displayed
  showvolume: false # Show volume (in fiat currency)
  showrank: false # Show ranking (by volume)
  24h: true # true for 24h clock, false for 12h
  locale: en_US # For region specific changes to price formatting
ticker:
  currency: bitcoin,ethereum,cardano # symbols used on coingecko
  exchange: default # specific exchanges can be specified
  fiatcurrency: usd,btc,gbp # 'fiat' currency
  sparklinedays: 1 # Time period shown on sparkline graph
  updatefrequency: 300 # How often price is refreshed (seconds) (lower limit 60s)
```

## Values

- **cycle**: switch the display between the listed currencies if set to **true**, display only the first on the list if set to **false**
- **cyclefiat**: cycle listed fiat currencies, display only the first on the list if set to **false**
- **inverted**: Black text on grey background if **false**. Grey text on black background if **true**
- **orientation**: Screen rotation in degrees , can take values **0,90,180,270**
- **trendingmode**: If **true**, it checks the 7 coins that coingecko lists as trending and also displays them (names are included in display)
- **showvolume, showrank**: **true** to include in display, **false** to omit
- **currency**: the coin(s) you would like to display (must be the coingecko id)
- **exchange**: default means use coingecko price, it can also be set to a specific exchange name such as **gdax** (coinbase), **binance** or **kraken** (full list on coingecko api [page](https://www.coingecko.com/api/documentations/v3)) 
- **fiatcurrency**: if **cyclefiat** is set to **True**, it will also cycle, otherwise it will use only the first entry (and cycle with button presses)
- **sparklinedays**: Number of days of historical data appearing on chart
- **updatefrequency**: (in seconds), how often to refresh the display

## Trending mode

When you activate trending mode (by setting to true in the config file, in addition to your coins, the ticker will cycle through 7 coins that are currently listing as trending on CoinGecko (see photo below).

![Action Shot](/images/actionshot/Trending.jpg)

# Contributing

To contribute, please fork the repository and use a feature branch. Pull requests are welcome.

# Links
[![Watch the video](https://img.youtube.com/vi/DNLUmJb7Mj8/maxresdefault.jpg)](https://youtu.be/DNLUmJb7Mj8) 
- Video of the unit working [here](https://youtu.be/DNLUmJb7Mj8)
- A fully assembled ticker or frames can be obtained at [veeb.ch](http://www.veeb.ch/)


# Licencing

GNU GENERAL PUBLIC LICENSE Version 3.0
