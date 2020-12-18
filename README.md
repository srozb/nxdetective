# nxdetective
Mass resolve 100k domains in less than 5 minutes, report non-existent ones.

The purpose of this script was to go through the list of every domain found in 
outbound smtp logs and find those non-existent and therefore ready to be 
registered by an adversary in order to collect mistakenly addressed emails.

![nxdetective in action](docs/action.gif)

## Requirements

* Python >= `3.7` (`3.8` is recommended)
* libs from `requirements.txt`

## Installation

```bash
clone this repo
python3 -m pip install -r requirements.txt
```

## Usage

```bash
python3 main.py process --nameservers 1.1.1.1,8.8.8.8 --workers_num 5 list.csv
```

Will spawn 10 asynchronous tasks (5 for `1.1.1.1` and 5 for `8.8.8.8`) and
resolve domains read from `list.csv` file. Non-existent domains will be written
to `report.csv`.

Example `list.csv`:

```csv
domain;popularity
example.org;1
e-xample.org;5
example.cn;3
e-x-ple.com;1
```

_(Note: `popularity` column is mandatory, but values are irrelevant and won't 
affect script's behaviour). Its only purpose is to indicate subjective 
popularity of the domain. This is useful if you take a list of domains from http 
or smtp logs and know exactly how popular it is within your environment._ 
