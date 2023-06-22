import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from uuid import uuid4

import openai
import streamlit as st

from utils.helpers import date_id
from utils.messages import (
    REINFORCEMENT_SYSTEM_MSG,
    INITIAL_SYSTEM_MSG,
    INTROS,
    CARDS_REINFORCEMENT_SYSTEM_MSG,
)
from utils.tarot import TAROT_DECK

SESSION_DIR = os.environ["SESSION_DIR"]

st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed",
    page_title="Emily Tarot - Virtual Tarot Readings",
)


IMAGE_DIR = (Path(__file__).parent / "images").relative_to(Path(__file__).parent)


def save_session():
    st.experimental_set_query_params(s=st.session_state.session_id)
    path = Path(SESSION_DIR) / (st.session_state.session_id + ".json")
    path.write_text(json.dumps(st.session_state.to_dict()))


@dataclass
class ChatSession:
    history: list = field(default_factory=list)

    def user_says(self, message):
        self.history.append({"role": "user", "content": message})

    def system_says(self, message):
        self.history.append({"role": "system", "content": message})

    def assistant_says(self, message):
        self.history.append({"role": "assistant", "content": message})


def init_state():
    query_session = st.experimental_get_query_params().get("s")
    if query_session:
        query_session = query_session[0]

        if (
            "session_id" in st.session_state
            and st.session_state.session_id != query_session
        ):
            st.session_state.clear()

    if "reading_in_progress" not in st.session_state:
        start_new_reading = True
        if query_session:
            path = Path(SESSION_DIR) / (query_session + ".json")
            try:
                loaded_session_data = json.loads(path.read_text())
            except:
                pass
            else:
                for k, v in loaded_session_data.items():
                    if not k.startswith("FormSubmitter"):
                        st.session_state[k] = v
                start_new_reading = False

        if start_new_reading:
            print("Starting new reading")
            st.session_state.reading_in_progress = True
            st.session_state.started_chat = False

            session_id = date_id()
            st.session_state.session_id = session_id
            imgs = random.sample(
                [str(x) for x in IMAGE_DIR.iterdir() if x.name != "emily.png"], k=4
            )
            st.session_state.header_images = [imgs[0], imgs[1], imgs[2]]
            st.session_state.emily_image = str(IMAGE_DIR / "emily.png")
            st.session_state.closing_image = imgs[3]

            cs = ChatSession()
            cs.assistant_says(random.choice(INTROS))
            st.session_state.chat_history = cs.history
            st.session_state.chosen_virtual_cards = []
            st.session_state.all_chosen_cards = []
            st.session_state.bad_responses = []
            st.session_state.total_tokens_used = 0


def initial_view():
    st.markdown(
        "<h1 style='text-align: center; color: purple;'>Shall we begin?</h1>",
        unsafe_allow_html=True,
    )

    card_draw_type = st.selectbox(
        "How would you like to select cards?",
        ["Draw cards virtually", "Draw cards from your own tarot deck"],
    )

    def _handle_click():
        st.session_state.card_draw_type = card_draw_type
        st.session_state.started_chat = True

    st.button("Yes", use_container_width=True, on_click=_handle_click)


@dataclass
class AiCommands:
    questions_to_ask: List[str]
    draw_cards: int
    cleaned_content: str


def _extract_commands(content: str) -> AiCommands:
    """Extract questions and number of cards to draw from the message; return the cleaned string without those cmds."""
    num_cards = 0
    questions = []
    remove_lines = []
    for line in content.splitlines():
        if line.startswith("QUESTION: "):
            questions.append(line.removeprefix("QUESTION: "))
            remove_lines.append(line)
        elif line.startswith("PULL TAROT CARDS"):
            _, num_cards_str = line.split(":")
            num_cards += int(num_cards_str)
            remove_lines.append(line)

    for line in remove_lines:
        content = content.replace(line, "")
    content = content.replace("\n\n\n", "\n\n")

    return AiCommands(
        questions_to_ask=questions, draw_cards=num_cards, cleaned_content=content
    )


def main():
    _, c1, c2, c3, _ = st.columns(5)
    c1.image(st.session_state.header_images[0])
    c2.image(st.session_state.header_images[1])
    c3.image(st.session_state.header_images[2])
    del c1, c2, c3

    if not st.session_state.started_chat:
        initial_view()
        return

    _, c1, _ = st.columns(3)
    c1.image(st.session_state.emily_image)
    del c1

    chat_session = ChatSession(history=st.session_state.chat_history)

    for msg in chat_session.history:
        if msg["role"] == "assistant":
            st.write(_extract_commands(msg["content"]).cleaned_content)
        elif msg["role"] == "user":
            st.write(
                f"<div style='color: yellow;'> &gt; {msg['content']}</div>",
                unsafe_allow_html=True,
            )
        elif msg["role"] == "system":
            if msg["content"].startswith("The selected cards were"):
                st.write(
                    f"<div style='color: red;'> &gt; {msg['content']}</div>",
                    unsafe_allow_html=True,
                )

    ai_commands = _extract_commands(chat_session.history[-1]["content"])

    if not (ai_commands.draw_cards or ai_commands.questions_to_ask):
        # reading is over
        _, c1, _ = st.columns(3)
        c1.image(st.session_state.closing_image)
        link = f"[Link to this session](?s={st.session_state.session_id})"
        c1.subheader(link)
        del c1
        if st.button("Return Home", use_container_width=True, type="primary"):
            st.experimental_set_query_params(s="")
            st.session_state.clear()
            st.experimental_rerun()
        return

    virtual_cards = st.session_state.card_draw_type == "Draw cards virtually"

    with st.form("user-input-form"):
        answers = []
        cards = []
        for question in ai_commands.questions_to_ask:
            answers.append(st.text_area(question))

        num_cards = 0
        if ai_commands.draw_cards:
            num_cards = ai_commands.draw_cards
            include_s = "s" if num_cards > 1 else ""
            st.write(f"Pull {num_cards} card{include_s}")

            if virtual_cards:
                if st.form_submit_button("Switch to your own Tarot deck"):
                    st.session_state.chosen_virtual_cards = []
                    st.session_state.card_draw_type = (
                        "Draw cards from your own tarot deck"
                    )
                    st.experimental_rerun()
                st.write("Use the buttons below to virtually shuffle and pull cards")
                c1, c2, c3, _ = st.columns((1, 1, 1, 2))
                shuffle_seed = c1.text_input(
                    "Shuffle Value",
                    value=st.session_state.get("shuffle_seed", uuid4().hex),
                    help="This value will be used to seed the random generator before drawing cards",
                )
                if shuffle_seed:
                    st.session_state.shuffle_seed = shuffle_seed

                if c2.form_submit_button("Shuffle"):
                    st.session_state.shuffle_seed = uuid4().hex
                    st.experimental_rerun()

                if c3.form_submit_button("Pull Card"):
                    if len(st.session_state.chosen_virtual_cards) == num_cards:
                        st.error("Already pulled requested number of cards")
                    else:
                        chosen = (
                            st.session_state.chosen_virtual_cards
                            + st.session_state.all_chosen_cards
                        )
                        card_puller = random.Random(shuffle_seed)
                        while (choice := card_puller.choice(TAROT_DECK)) in chosen:
                            pass
                        st.session_state.chosen_virtual_cards.append(choice)
                        st.experimental_rerun()
                for x in range(num_cards):
                    try:
                        chosen = st.session_state.chosen_virtual_cards[x]
                    except IndexError:
                        chosen = ""
                    cards.append(
                        st.text_input(f"Card {x+1}", value=chosen, disabled=True)
                    )

            else:
                if st.form_submit_button("Switch to drawing virtual cards"):
                    st.session_state.chosen_virtual_cards = []
                    st.session_state.card_draw_type = "Draw cards virtually"
                    st.experimental_rerun()
                st.write("Shuffle your deck and pull cards as instructed")
                deck = [""] + TAROT_DECK
                for x in range(num_cards):
                    try:
                        chosen = st.session_state.chosen_virtual_cards[x]
                        select_index = deck.index(chosen)
                    except IndexError:
                        select_index = 0
                    cards.append(
                        st.selectbox(
                            f"Card {x+1}",
                            deck,
                            index=select_index,
                            disabled=virtual_cards,
                        )
                    )
        if st.form_submit_button("Submit"):
            can_submit = True
            if len([x for x in answers if x]) != len(ai_commands.questions_to_ask):
                can_submit = False
            if len([x for x in cards if x]) != num_cards:
                can_submit = False

            if not can_submit:
                st.error("Answer all questions and draw all cards before submitting")
            elif len(cards) != len(set(cards)):
                st.error("Cannot choose the same card more than once")
                can_submit = False

            if can_submit:
                # combine the user answers into a single response, and check it for restricted content
                if answers:
                    combined_answer = "\n\n".join(answers)
                    chat_session.user_says(combined_answer)
                    _check_user_message(combined_answer)
                if cards:
                    chat_session.system_says(
                        "The selected cards were: " + ", ".join(cards)
                    )
                    st.session_state.all_chosen_cards.extend(cards)
                    st.session_state.chosen_virtual_cards = []
                with st.spinner("Generating AI response"):
                    got_valid_response = False
                    attempts = 0
                    max_attempts = 3
                    while not got_valid_response:
                        attempts += 1
                        response = _get_ai_response(chat_session)
                        try:
                            _extract_commands(
                                response["choices"][0]["message"]["content"]
                            )
                            break
                        except Exception:
                            print("Got bad response, trying again")
                            st.session_state.bad_responses.append(response)
                            st.session_state.total_tokens_used += response["usage"][
                                "total_tokens"
                            ]
                            if attempts >= max_attempts:
                                print("Out of attempts")
                                st.error(
                                    "Encountered an error generating your reading, sorry about that"
                                )
                                return

                st.session_state.total_tokens_used += response["usage"]["total_tokens"]

                chat_session.assistant_says(
                    response["choices"][0]["message"]["content"]
                )

                save_session()
                st.experimental_rerun()

    if len(chat_session.history) > 1:
        save_session()


class FlaggedInputError(RuntimeError):
    pass


def _check_user_message(msg: str):
    response = openai.Moderation.create(msg)
    if response.results[0].flagged:
        raise FlaggedInputError()


def _get_ai_response(chat_session: ChatSession):
    chat_history = chat_session.history[:]
    # add the initial system message describing the AI's role
    chat_history.insert(0, {"role": "system", "content": INITIAL_SYSTEM_MSG})

    # now add a reinforcing message for the AI, based on whether we are interpreting cards right now or not
    last_msg = chat_history[-1]
    if last_msg["role"] == "system" and last_msg["content"].startswith(
        "The selected cards were"
    ):
        chat_history.append(
            {"role": "system", "content": CARDS_REINFORCEMENT_SYSTEM_MSG}
        )
    else:
        chat_history.append({"role": "system", "content": REINFORCEMENT_SYSTEM_MSG})

    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=chat_history,
    )


init_state()
try:
    if "flagged_input" in st.session_state:
        st.write("This session has been terminated")
        st.write(
            "I'm really sorry that you're feeling this way, but I'm unable to provide the help that you need. "
            "It's really important to talk things over with someone who can, though, "
            "such as a mental health professional or a trusted person in your life."
        )

        st.markdown(
            """
            * 988 Suicide & Crisis Lifeline: https://988lifeline.org/ has phone and chat optionas available
            * International suicide hotlines: A comprehensive resource list for people outside the U.S. can be found [here](http://www.suicide.org/hotlines/international-suicide-hotlines.html).
            """
        )
        st.write("**Remember, you're not alone. There are people who want to help.**")
    else:
        main()
        st.caption(
            "All art and text generated by Artificial Intelligence - for entertainment purposes only"
        )
        st.caption("View on [Github](https://github.com/msull/emilytarot)")

        with st.expander("Session State", expanded=False):
            st.write(st.session_state)
except FlaggedInputError:
    st.error("FLAGGED INPUT RECEIVED")
    st.session_state.flagged_input = True
    save_session()
    st.experimental_rerun()
