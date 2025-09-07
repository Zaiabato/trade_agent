import pandas as pd
import numpy as np
import torch
try:
    import pandas_ta as ta
except ImportError:
    from ta.trend import SMAIndicator as ta
import dotenv
import streamlit
import plotly
import telegram

print("All dependencies imported successfully!")
