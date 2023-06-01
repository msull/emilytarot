from pathlib import Path

import streamlit as st

from pydantic import BaseSettings
import random

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
if "reading_started" not in st.session_state:
    st.session_state.reading_started = False


class Settings(BaseSettings):
    app_debug: bool = False


# @st.cache_resource
def get_settings():
    return Settings()


SETTINGS = get_settings()
if not SETTINGS.app_debug:
    hide_menu_style = """
            <style>
            html { font-size: 140%;} 
            footer {visibility: hidden;}
            #MainMenu {visibility: hidden;}
            </style>
            """
    st.markdown(hide_menu_style, unsafe_allow_html=True)


class RandomSelector:
    def __init__(self, input_list):
        self.input_list = input_list
        self.selected = []

    def select(self):
        if len(self.input_list) == 0:
            raise ValueError("All elements have been selected.")
        selected_element = random.choice(self.input_list)
        self.input_list.remove(selected_element)
        self.selected.append(selected_element)
        return selected_element


IMAGE_DIR = (Path(__file__).parent / "images").relative_to(Path(Path(__file__).parent))
IMAGE_SELECTOR = RandomSelector([str(x) for x in IMAGE_DIR.iterdir()])


def initial_view():
    options = []
    c1, c2, c3 = st.columns(3)
    c1.image(IMAGE_SELECTOR.select())
    options.append(c2)
    options.append(c3)


    c1, c2, c3 = st.columns(3)
    c2.image(IMAGE_SELECTOR.select())
    options.append(c1)
    options.append(c3)


    c1, c2, c3 = st.columns(3)
    c3.image(IMAGE_SELECTOR.select())
    options.append(c1)
    options.append(c2)

    column = random.choice(options)
    column.write("Have you come for a reading?")



    #
    # g1c1, g1c2, g1c3 = st.columns((1, 2,1))
    # g1c2.image(IMAGE_SELECTOR.select())
    # # g1c2.markdown('')
    # # g1c3.image(IMAGE_SELECTOR.select())
    #
    # g2c1, g2c2, g2c3 = st.columns((2, 1, 2))
    # g2c1.image(IMAGE_SELECTOR.select())
    # g2c2.write('Have you come for a reading?')
    # g2c3.image(IMAGE_SELECTOR.select())


def reading_underway_view():
    pass


if not st.session_state.reading_started:
    initial_view()
else:
    reading_underway_view()
