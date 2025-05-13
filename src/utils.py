import configparser

from prettytable import PrettyTable
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def print_config(config):
    config_table = PrettyTable()
    config_table.field_names = ["Config", "Value"]
    config_table.align = "l"
    for section in config.sections():
        for key in config[section]:
            config_table.add_row([key, config[section][key]])
    print(config_table)


def load_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)

    # print_config(config)

    return config

# You can define your own condition here to check if the new date is valid
# for example: def MY_CONDITION(month, day): return int(month) == 11 and int(day) >= 5
# This means that the new date should be in November and the day should be greater than or equal to 5

# No custom condition wanted for the new scheduled date
def my_condition(month, day):
    return None

def get_driver(local_use, hub_address, watch_bot):
    """
    Get driver instance based on LOCAL_USE flag.
    """
    options = Options()
    try:
        if local_use:
            # Explicitly set the path to the ChromeDriver executable
            chromedriver_path = ChromeDriverManager().install()
            print(f"Using ChromeDriver at path: {chromedriver_path}")  # Debugging statement
            driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
        else:
            driver = webdriver.Remote(command_executor=hub_address, options=options)
        
        # Minimize or center the window based on the watch_bot parameter
        print(f"Watch Bot in get_driver: {watch_bot}")  # Debugging statement
        if watch_bot:
            driver.set_window_position(0, 0)  # Center the window
        else:
            driver.set_window_position(-10000, 0)  # Move the window away
        
        return driver
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        raise
