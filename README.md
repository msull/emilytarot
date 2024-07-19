# Emily Tarot

Emily Tarot is a techno-mystic project that leverages OpenAI's GPT-3.5-turbo for generating Tarot card readings. This
project was designed as an experiment to learn Streamlit and to explore working with large language models for custom
applications. Hosted at [EmilyTarot.com](http://emilytarot.com).

> Note: This project is now using the incredible GPT-4-omni-mini model!

## Features

* User Interface: The project uses Streamlit to create a visually engaging and intuitive interface for the users to
  interact with.
* Techno-Mystic Experience: Users are guided through a Tarot reading session where they can choose from a virtual deck
  of Tarot cards or use their own physical deck.
* AI Interaction: The selected cards and user's questions are processed by OpenAI's GPT-3.5-turbo model to generate a
  personalized Tarot reading.
* Session Persistence: The state of the current session is maintained across Streamlit reruns, providing a continuous
  experience to the user.
* Moderation: The user's input is checked and moderated for any inappropriate content, terminating the session and
  displaying crisis resources when user content is flagged
* Docker Support: A Dockerfile and docker-compose files are included to facilitate the deployment and running of the
  application.

## Usage

To run Emily Tarot locally, follow these steps:

1. Clone this repository.
2. Install the dependencies: `pip install -r requirements.txt`
3. Set up environment variables `SESSION_DIR` and `OPENAI_SECRET_KEY`.
4. Use `cd src && streamlit src/streamlit_app.py` to start the Streamlit application.
5. Navigate to `http://localhost:8501` in your web browser to interact with Emily Tarot.

To build and run Emily Tarot with Docker:

1. `docker-compose build`
2. `docker-compose up`
3. The application should be available at `http://localhost:9999`.

## License

This project is licensed under the terms of the MIT license.
