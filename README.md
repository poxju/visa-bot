# visa-bot

visa-bot is my personal automation tool designed to assist with visa application processes. It can automate form submissions, check appointment availability, and send notifications.

> There are many approaches to visa bots on GitHub, but this repository contains my own implementation.  Changes can always be made to the visa site. Therefore the script may not work properly. Please use it carefully.

## Features

- Automates visa application form filling
- Checks for available appointment slots
- Sends notifications via email or messaging platforms

## Requirements

- Python 3.8+  
- See `requirements.txt` for Python dependencies

## Setup

1. Clone the repository:
   ```sh
   git clone https://github.com/poxju/visa-bot.git
   cd visa-bot
   ```

2. Install Python dependencies:
   ```sh
   pip install -r requirements.txt
   ```

3. Configure environment variables or edit the configuration files as needed (e.g., `src/config.ini`).

## Usage

Run the main bot:
```sh
python src/main.py
```
If you want to use with a GUI:
```sh
python src/gui.py
```
