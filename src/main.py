from dotenv import load_dotenv
from wasabi import msg

load_dotenv()


def main():
    """Launch the Recipe Board Gradio UI."""
    from recipe_board.gradio_ui import launch_ui

    # with open("./data/claudes-lasagne.md", 'r', encoding='utf-8') as file:
    #     parse_steps(file.read())
    msg.info("Starting Recipe Board UI...")
    launch_ui()


if __name__ == "__main__":
    main()
