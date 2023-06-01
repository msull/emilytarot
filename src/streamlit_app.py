from pathlib import Path

import streamlit as st

from pydantic import BaseSettings
import random

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")


class States:
    initial = "initial"
    gathering_description = "gathering_description"


if "progress" not in st.session_state:
    st.session_state.progress = States.initial


class Settings(BaseSettings):
    app_debug: bool = False


# @st.cache_resource
def get_settings():
    return Settings()


SETTINGS = get_settings()
if not SETTINGS.app_debug:
    hide_menu_style = """
            <style>
            # html { font-size: 140%;} 
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
    _, c1, c2, c3, _ = st.columns(5)
    c1.image(IMAGE_SELECTOR.select())
    c2.image(IMAGE_SELECTOR.select())
    c3.image(IMAGE_SELECTOR.select())
    del c1, c2, c3

    st.markdown(
        "<h1 style='text-align: center; color: purple;'>Have you come for a reading?</h1>",
        unsafe_allow_html=True,
    )

    def _handle_click():
        st.session_state.progress = States.gathering_description

    st.button("Yes", use_container_width=True, on_click=_handle_click)

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


def gather_info_view():
    _, c1,  _ = st.columns(3)
    c1.image(IMAGE_SELECTOR.select())
    del c1

    st.markdown(
        "<h2 style='text-align: center; color: purple;'>Good.<br />First you must tell me about yourself.</h2>",
        unsafe_allow_html=True,
    )

    with st.form("description-form"):
        st.markdown(
            "<h3 style='text-align: center; color: purple;'>Who are you?</h3>",
            unsafe_allow_html=True,
        )
        self_description = st.text_area(
            "Enter a brief description of yourself, perhaps share a bit about your beliefs, tarot experience, background or anything else.",
        )
        card_draw_type = st.selectbox(
            "How would you like to select cards?",
            ["Draw cards virtually", "Draw cards from your own tarot deck"],
        )
        st.form_submit_button()

    _, c1, c2, c3, _ = st.columns(5)
    c1.image(IMAGE_SELECTOR.select())
    c2.image(IMAGE_SELECTOR.select())
    c3.image(IMAGE_SELECTOR.select())
    del c1, c2, c3


this_state = st.session_state.progress
if this_state == States.initial:
    initial_view()
elif this_state == States.gathering_description:
    gather_info_view()
else:
    pass
st.write('&nbsp;')
st.write('&nbsp;')
st.write('&nbsp;')
st.write('&nbsp;')
_, c = st.columns((5, 1))
if c.button("Restart"):
    st.session_state.clear()
    # st.session_state.progress = States.initial
    st.experimental_rerun()
