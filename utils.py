# dafault libs
import os
import json

# required stuff
from dotenv import load_dotenv

# custom exceptions
from exceptions import EnvNotConfiguredException

# custom objects
from config import Config


# pre-setup
config: Config = None
load_dotenv()


def get_api_key() -> str:
    """
    Get the api key for Gemini.
    
    Returns:
        str: the api key as a string.
        
    Raises:
        EnvNotConfiguredException: if GEMINI_API_KEY is not configured in .env 
    """
    
    api_key: str = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.startswith("YOUR_"):
        raise EnvNotConfiguredException("Please setup GEMINI_API_KEY in the .env")
    
    return api_key
    

def get_gemini_model() -> str:
    """
    Get the model name for Gemini.
    
    Returns:
        str: the gemini model name as a string.
        
    Raises:
        EnvNotConfiguredException: if GEMINI_MODEL is not configured in .env 
    """
    
    model_name: str = os.getenv("GEMINI_MODEL")
    if not model_name or model_name.startswith("YOUR_"):
        raise EnvNotConfiguredException("Please setup GEMINI_MODEL in the .env")
    
    return model_name


def load_config() -> None:
    """
    Initializes the configuration object.
    """
    
    global config
    with open("config.json", "r") as file:
        config_data = json.load(file)
        
    config = Config(config_data)
    

load_config()

