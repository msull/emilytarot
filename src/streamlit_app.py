import streamlit as st




st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

hide_menu_style = """
        <style>
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.image(
    "images/DALL·E 2023-06-01 13.41.10 - a stained glass tarot card reading scene.png"
)


def initial_view():
    pass


def reading_underway_view():
    pass
